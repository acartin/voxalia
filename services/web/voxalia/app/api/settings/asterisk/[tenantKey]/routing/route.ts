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
  if (payload.channel_id === "") payload.channel_id = null;
  if (payload.number_id === "") payload.number_id = null;
  if (payload.inbound_context_id === "") payload.inbound_context_id = null;
  if (typeof payload.channel_id === "string") payload.channel_id = Number(payload.channel_id);
  if (typeof payload.number_id === "string") payload.number_id = Number(payload.number_id);
  if (typeof payload.inbound_context_id === "string") payload.inbound_context_id = Number(payload.inbound_context_id);
  if (typeof payload.priority === "string") payload.priority = Number(payload.priority);
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

  const response = await fetch(`${ASTERISK_API_BASE_URL}/asterisk/tenants/${encodeURIComponent(tenantKey)}/routing`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store"
  });

  if (!response.ok) {
    const errorPayload = await response.json().catch(() => undefined);
    return redirectPath(request, "error", friendlyApiError(errorPayload));
  }

  return redirectPath(request, "success", "Routing rule created successfully.");
}
