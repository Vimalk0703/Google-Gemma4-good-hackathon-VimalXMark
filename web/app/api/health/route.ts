import { NextResponse } from "next/server";
import { cookies } from "next/headers";

export const runtime = "nodejs";
export const maxDuration = 10;

const COOKIE_NAME = "malaika_portal_session";

export async function GET() {
  const jar = await cookies();
  if (jar.get(COOKIE_NAME)?.value !== "1") {
    return NextResponse.json({ ok: false, error: "Not authenticated." }, { status: 401 });
  }

  const endpoint = process.env.BREATH_API_URL;
  if (!endpoint) {
    return NextResponse.json({
      ok: false,
      configured: false,
      error: "BREATH_API_URL is not set on this deployment.",
    });
  }

  const t0 = performance.now();
  try {
    const upstream = await fetch(`${endpoint.replace(/\/$/, "")}/health`, {
      method: "GET",
      signal: AbortSignal.timeout(5000),
      cache: "no-store",
    });
    const latencyMs = Math.round(performance.now() - t0);

    if (!upstream.ok) {
      return NextResponse.json({
        ok: false,
        configured: true,
        error: `Server responded ${upstream.status}.`,
        latencyMs,
      });
    }

    let payload: Record<string, unknown> = {};
    try {
      payload = await upstream.json();
    } catch {
      // Server returned non-JSON — still OK if status was 200.
    }

    return NextResponse.json({
      ok: true,
      configured: true,
      latencyMs,
      model: typeof payload.model === "string" ? payload.model : undefined,
      status: typeof payload.status === "string" ? payload.status : "ok",
    });
  } catch (err) {
    return NextResponse.json({
      ok: false,
      configured: true,
      error:
        err instanceof Error && err.name === "TimeoutError"
          ? "Health check timed out after 5 seconds."
          : "Could not reach the clinic server.",
      latencyMs: Math.round(performance.now() - t0),
    });
  }
}
