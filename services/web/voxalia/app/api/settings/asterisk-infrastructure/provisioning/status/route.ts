import { NextResponse } from "next/server";
import { ASTERISK_API_BASE_URL, sessionCookieName } from "@/lib/api";

function tokenFromRequest(request: Request): string | undefined {
  return request.headers
    .get("cookie")
    ?.split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith(`${sessionCookieName}=`))
    ?.split("=")[1];
}

export async function GET(request: Request) {
  const token = tokenFromRequest(request);
  if (!token) return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  if (!ASTERISK_API_BASE_URL) return NextResponse.json({ detail: "Asterisk API not configured" }, { status: 500 });

  const response = await fetch(`${ASTERISK_API_BASE_URL}/asterisk/workspace`, {
    cache: "no-store"
  });

  if (!response.ok) {
    return NextResponse.json({ detail: "Asterisk API unavailable" }, { status: response.status });
  }

  const payload = await response.json();
  const applyState = payload.sections?.find((section: Record<string, unknown>) => section.id === "tenant_apply_state");
  const records = Array.isArray(applyState?.records) ? applyState.records as Array<Record<string, unknown>> : [];
  const pending = records.filter((record) => String(record.status ?? "").toLowerCase() === "pending");
  const failed = records.filter((record) => String(record.status ?? "").toLowerCase() === "failed");
  const status = failed.length > 0 ? "failed" : pending.length > 0 ? "pending" : "applied";
  const pendingChanges = pending.reduce((total, record) => total + Number(record.pending_changes ?? 0), 0);
  const pendingDetails = pending
    .map((record) => `${record.tenant}: ${record.pending_details}`)
    .filter(Boolean);

  return NextResponse.json({
    status,
    pending_scopes: pending.length,
    failed_scopes: failed.length,
    pending_changes: pendingChanges,
    pending_details: pendingDetails
  });
}
