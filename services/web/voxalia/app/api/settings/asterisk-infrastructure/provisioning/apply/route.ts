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
  const fallback = "/settings/asterisk-infrastructure";
  const target = referer ? new URL(referer).pathname + new URL(referer).search : fallback;
  const separator = target.includes("?") ? "&" : "?";
  return redirectTo(`${target}${separator}${feedbackQuery(type, message)}`);
}

export async function POST(request: Request) {
  const token = tokenFromRequest(request);
  if (!token) return redirectTo("/login");
  if (!ASTERISK_API_BASE_URL) return NextResponse.json({ detail: "Asterisk API not configured" }, { status: 500 });

  const response = await fetch(`${ASTERISK_API_BASE_URL}/asterisk/provisioning/apply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode: "apply" }),
    cache: "no-store"
  });

  if (!response.ok) {
    const errorPayload = await response.json().catch(() => undefined);
    return redirectPath(request, "error", friendlyApiError(errorPayload));
  }

  return redirectPath(request, "success", "Asterisk config applied to Voxalia-managed files.");
}
