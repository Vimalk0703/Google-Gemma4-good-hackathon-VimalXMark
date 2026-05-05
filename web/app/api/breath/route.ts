import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

export const runtime = "nodejs";
export const maxDuration = 120;

const COOKIE_NAME = "malaika_portal_session";

export async function POST(request: NextRequest) {
  const jar = await cookies();
  if (jar.get(COOKIE_NAME)?.value !== "1") {
    return NextResponse.json({ error: "Not authenticated." }, { status: 401 });
  }

  const endpoint = process.env.BREATH_API_URL;
  if (!endpoint) {
    return NextResponse.json(
      { error: "Server endpoint not configured. Set BREATH_API_URL in the deployment environment." },
      { status: 503 }
    );
  }

  let inboundForm: FormData;
  try {
    inboundForm = await request.formData();
  } catch {
    return NextResponse.json({ error: "Invalid form payload." }, { status: 400 });
  }

  const audio = inboundForm.get("audio");
  if (!(audio instanceof File)) {
    return NextResponse.json({ error: "Missing audio file." }, { status: 400 });
  }

  const MAX_BYTES = 25 * 1024 * 1024;
  if (audio.size === 0 || audio.size > MAX_BYTES) {
    return NextResponse.json(
      { error: `Audio must be between 1 byte and 25 MB (got ${audio.size}).` },
      { status: 413 }
    );
  }

  const upstreamForm = new FormData();
  upstreamForm.append("audio", audio, audio.name || "recording.wav");

  const t0 = performance.now();
  let upstream: Response;
  try {
    upstream = await fetch(`${endpoint.replace(/\/$/, "")}/breath`, {
      method: "POST",
      body: upstreamForm,
      signal: AbortSignal.timeout(115_000),
    });
  } catch {
    return NextResponse.json(
      { error: "Could not reach the clinic server. Check that the notebook 12 endpoint is running." },
      { status: 502 }
    );
  }
  const latencyMs = Math.round(performance.now() - t0);

  let payload: Record<string, unknown>;
  try {
    payload = await upstream.json();
  } catch {
    return NextResponse.json(
      { error: "Server returned an unparseable response." },
      { status: 502 }
    );
  }

  if (!upstream.ok) {
    return NextResponse.json(
      { error: typeof payload.error === "string" ? payload.error : "Upstream error." },
      { status: upstream.status }
    );
  }

  return NextResponse.json({
    abnormal: Boolean(payload.abnormal),
    confidence: typeof payload.confidence === "number" ? payload.confidence : undefined,
    description: typeof payload.description === "string" ? payload.description : undefined,
    clinicalNote: typeof payload.clinical_note === "string" ? payload.clinical_note : undefined,
    clinicalNoteError:
      typeof payload.clinical_note_error === "string" ? payload.clinical_note_error : undefined,
    raw: typeof payload.raw === "string" ? payload.raw : undefined,
    latencyMs,
  });
}
