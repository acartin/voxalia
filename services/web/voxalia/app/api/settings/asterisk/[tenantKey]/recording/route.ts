import { NextResponse } from "next/server";
import { ASTERISK_API_BASE_URL, sessionCookieName } from "@/lib/api";
import { feedbackQuery, friendlyApiError } from "@/lib/feedback";
import { redirectTo } from "@/lib/request-url";

function tokenFromRequest(request: Request): string | undefined {
  return request.headers
    .get("cookie")
    ?.split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith(`${sessionCookieName}=`))
    ?.split("=")[1];
}

function redirectPath(request: Request, type: "success" | "error", message: string) {
  const referer = request.headers.get("referer");
  const fallback = "/settings/asterisk";
  const target = referer ? new URL(referer).pathname + new URL(referer).search : fallback;
  const separator = target.includes("?") ? "&" : "?";
  return redirectTo(`${target}${separator}${feedbackQuery(type, message)}`);
}

function payloadFromForm(formData: FormData) {
  const payload: Record<string, unknown> = Object.fromEntries(formData.entries());
  if (payload.recording_required === "true") payload.recording_required = true;
  if (payload.recording_required === "false") payload.recording_required = false;
  if (payload.disclosure_required === "true") payload.disclosure_required = true;
  if (payload.disclosure_required === "false") payload.disclosure_required = false;
  if (typeof payload.retention_days === "string") payload.retention_days = Number(payload.retention_days);
  if (payload.scope_id === "") payload.scope_id = "";
  if (typeof payload.config === "string" && payload.config.trim()) payload.config = JSON.parse(payload.config);
  if (payload.config === "") payload.config = {};
  return payload;
}

export async function POST(request: Request, { params }: { params: Promise<{ tenantKey: string }> }) {
  const token = tokenFromRequest(request);
  if (!token) return redirectTo("/login");
  if (!ASTERISK_API_BASE_URL) return NextResponse.json({ detail: "Asterisk API not configured" }, { status: 500 });

  const { tenantKey } = await params;
  const formData = await request.formData();
  let payload: Record<string, unknown>;
  try {
    payload = payloadFromForm(formData);
  } catch {
    return redirectPath(request, "error", "Config must be a valid JSON object.");
  }

  const response = await fetch(`${ASTERISK_API_BASE_URL}/asterisk/tenants/${encodeURIComponent(tenantKey)}/recording`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store"
  });

  if (!response.ok) {
    const errorPayload = await response.json().catch(() => undefined);
    return redirectPath(request, "error", friendlyApiError(errorPayload));
  }

  return redirectPath(request, "success", "Recording policy created successfully.");
}
