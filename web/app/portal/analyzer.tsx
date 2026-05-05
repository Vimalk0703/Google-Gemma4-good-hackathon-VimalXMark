"use client";

import { useEffect, useRef, useState } from "react";

const MAX_RECORDING_SECONDS = 60;
const TARGET_SAMPLE_RATE = 22050; // matches notebook 06 / 12 librosa pipeline

type RecorderState =
  | { state: "idle" }
  | { state: "requesting" }
  | { state: "recording"; seconds: number }
  | { state: "encoding" }
  | { state: "error"; message: string };

type InputMode = "upload" | "record";

type AnalysisResult =
  | {
      ok: true;
      abnormal: boolean;
      confidence?: number;
      description?: string;
      clinicalNote?: string;
      clinicalNoteError?: string;
      raw?: string;
      latencyMs: number;
      filename: string;
      timestamp: number;
    }
  | { ok: false; error: string };

type HealthState =
  | { state: "checking" }
  | { state: "ready"; latencyMs: number; model?: string }
  | { state: "unconfigured"; message: string }
  | { state: "down"; message: string; latencyMs?: number };

type Stage = "idle" | "uploading" | "spectrogram" | "inference" | "done";

const ACCEPTED = ".wav,.mp3,.m4a,audio/wav,audio/mpeg,audio/mp4,audio/x-m4a";
const HISTORY_LIMIT = 3;

export function Analyzer() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startedAtRef = useRef<number>(0);

  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [history, setHistory] = useState<Extract<AnalysisResult, { ok: true }>[]>([]);
  const [stage, setStage] = useState<Stage>("idle");
  const [dragging, setDragging] = useState(false);
  const [health, setHealth] = useState<HealthState>({ state: "checking" });
  const [inputMode, setInputMode] = useState<InputMode>("upload");
  const [recorder, setRecorder] = useState<RecorderState>({ state: "idle" });

  // Health check on mount + after each analyze attempt
  useEffect(() => {
    void checkHealth();
  }, []);

  // Manage object URLs for audio preview
  useEffect(() => {
    if (!file) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  async function checkHealth() {
    setHealth({ state: "checking" });
    try {
      const res = await fetch("/api/health", { cache: "no-store" });
      const data = await res.json();
      if (data.ok) {
        setHealth({ state: "ready", latencyMs: data.latencyMs, model: data.model });
      } else if (data.configured === false) {
        setHealth({ state: "unconfigured", message: data.error });
      } else {
        setHealth({ state: "down", message: data.error, latencyMs: data.latencyMs });
      }
    } catch {
      setHealth({ state: "down", message: "Could not reach the local API." });
    }
  }

  function handleFile(f: File | null | undefined) {
    if (!f) return;
    setFile(f);
    setResult(null);
    setStage("idle");
  }

  function clearFile() {
    setFile(null);
    setResult(null);
    setStage("idle");
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  // ---------- Microphone recording (encodes to WAV in the browser) ----------

  function tearDownStream() {
    if (tickRef.current) {
      clearInterval(tickRef.current);
      tickRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    recorderRef.current = null;
  }

  async function startRecording() {
    setResult(null);
    setRecorder({ state: "requesting" });
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, sampleRate: TARGET_SAMPLE_RATE, echoCancellation: false, noiseSuppression: false },
      });
      streamRef.current = stream;

      const mr = new MediaRecorder(stream);
      const chunks: Blob[] = [];
      mr.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunks.push(e.data);
      };
      mr.onstop = async () => {
        try {
          setRecorder({ state: "encoding" });
          const captured = new Blob(chunks, { type: chunks[0]?.type || "audio/webm" });
          const wavFile = await encodeBlobAsWav(captured);
          handleFile(wavFile);
          setInputMode("record"); // keep on record view so the user sees the preview here
          setRecorder({ state: "idle" });
        } catch (err) {
          setRecorder({
            state: "error",
            message:
              err instanceof Error
                ? `Could not encode the recording (${err.message}). Try again.`
                : "Could not encode the recording.",
          });
        } finally {
          tearDownStream();
        }
      };

      recorderRef.current = mr;
      startedAtRef.current = Date.now();
      mr.start();
      setRecorder({ state: "recording", seconds: 0 });

      tickRef.current = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startedAtRef.current) / 1000);
        if (elapsed >= MAX_RECORDING_SECONDS) {
          stopRecording();
        } else {
          setRecorder({ state: "recording", seconds: elapsed });
        }
      }, 250);
    } catch (err) {
      tearDownStream();
      const msg =
        err instanceof Error && err.name === "NotAllowedError"
          ? "Microphone permission denied. Allow it in your browser address bar and try again."
          : "Could not access the microphone on this device.";
      setRecorder({ state: "error", message: msg });
    }
  }

  function stopRecording() {
    if (recorderRef.current && recorderRef.current.state === "recording") {
      recorderRef.current.stop();
    }
  }

  // Tear down any live mic stream when the component unmounts
  useEffect(() => {
    return () => tearDownStream();
  }, []);

  async function handleAnalyze() {
    if (!file || stage !== "idle") return;
    setResult(null);
    setStage("uploading");

    const fd = new FormData();
    fd.append("audio", file);

    // Walk the user through the perceived stages while the request is in flight.
    // This matches notebook 12's actual server pipeline (upload → spectrogram → inference).
    const stageTimer1 = setTimeout(() => setStage("spectrogram"), 600);
    const stageTimer2 = setTimeout(() => setStage("inference"), 1500);

    try {
      const res = await fetch("/api/breath", { method: "POST", body: fd });
      const data = await res.json();
      clearTimeout(stageTimer1);
      clearTimeout(stageTimer2);

      if (!res.ok) {
        setResult({ ok: false, error: data?.error ?? "Analysis failed." });
      } else {
        const success: Extract<AnalysisResult, { ok: true }> = {
          ok: true,
          abnormal: Boolean(data.abnormal),
          confidence: typeof data.confidence === "number" ? data.confidence : undefined,
          description: typeof data.description === "string" ? data.description : undefined,
          clinicalNote: typeof data.clinicalNote === "string" ? data.clinicalNote : undefined,
          clinicalNoteError:
            typeof data.clinicalNoteError === "string" ? data.clinicalNoteError : undefined,
          raw: typeof data.raw === "string" ? data.raw : undefined,
          latencyMs: typeof data.latencyMs === "number" ? data.latencyMs : 0,
          filename: file.name,
          timestamp: Date.now(),
        };
        setResult(success);
        setHistory((prev) => [success, ...prev].slice(0, HISTORY_LIMIT));
      }
    } catch {
      clearTimeout(stageTimer1);
      clearTimeout(stageTimer2);
      setResult({ ok: false, error: "Could not reach the analyzer. Check your connection." });
    } finally {
      setStage("done");
      setTimeout(() => setStage("idle"), 200);
      void checkHealth();
    }
  }

  return (
    <div className="space-y-10">
      <ConnectionBanner health={health} onRefresh={checkHealth} />

      {/* Step 1 — Audio source (upload or record) */}
      <section>
        <div className="mb-4 flex items-baseline justify-between gap-4">
          <p className="eyebrow">Step 1 · Audio</p>
          <ModeTabs
            mode={inputMode}
            disabled={recorder.state === "recording" || recorder.state === "encoding"}
            onChange={(m) => {
              setInputMode(m);
              setRecorder({ state: "idle" });
            }}
          />
        </div>

        {inputMode === "upload" ? (
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              handleFile(e.dataTransfer.files?.[0]);
            }}
            className="relative cursor-pointer p-12 text-center transition-colors"
            style={{
              background: dragging ? "var(--color-amber-soft)" : "var(--color-paper)",
              border: `1px dashed ${dragging ? "var(--color-amber-deep)" : "var(--color-line-strong)"}`,
              borderRadius: "var(--radius-card)",
            }}
            onClick={() => fileInputRef.current?.click()}
            role="button"
            tabIndex={0}
            aria-label="Upload audio file for breath sound analysis"
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click();
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED}
              className="hidden"
              onChange={(e) => handleFile(e.target.files?.[0])}
            />
            {file ? (
              <div>
                <p className="font-display text-xl" style={{ color: "var(--color-ink)" }}>
                  {file.name}
                </p>
                <p className="mt-2 text-sm tabular" style={{ color: "var(--color-muted)" }}>
                  {(file.size / 1024 / 1024).toFixed(2)} MB · {file.type || "audio"}
                </p>
                <p className="mt-4 text-xs" style={{ color: "var(--color-faint)" }}>
                  Click or drop another file to replace.
                </p>
              </div>
            ) : (
              <div>
                <p className="font-display text-xl" style={{ color: "var(--color-ink)" }}>
                  Drop a recording here
                </p>
                <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--color-muted)" }}>
                  WAV, MP3, or M4A. Up to two minutes. The audio is sent only to
                  the clinic server you have configured. It is not logged or
                  persisted.
                </p>
              </div>
            )}
          </div>
        ) : (
          <RecorderPanel
            recorder={recorder}
            file={file}
            onStart={startRecording}
            onStop={stopRecording}
            onClear={clearFile}
          />
        )}

        {file && previewUrl ? (
          <div
            className="mt-5 flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between"
            style={{
              background: "var(--color-paper)",
              border: "1px solid var(--color-line)",
              borderRadius: "var(--radius-card)",
            }}
          >
            <div className="flex-1 sm:max-w-md">
              <p className="eyebrow mb-2">Preview</p>
              <audio
                controls
                src={previewUrl}
                preload="metadata"
                className="w-full"
                style={{ height: 36 }}
              />
            </div>
            <button
              type="button"
              onClick={clearFile}
              className="text-sm link-underline self-start sm:self-center"
              style={{ color: "var(--color-muted)" }}
            >
              Clear
            </button>
          </div>
        ) : null}

        {!file ? <SampleHint /> : null}
      </section>

      {/* Analyze action */}
      <section>
        <p className="eyebrow mb-3">Step 2 · Analyze</p>
        <div
          className="flex flex-col items-start gap-4 p-6 sm:flex-row sm:items-center sm:justify-between"
          style={{
            background: "var(--color-paper)",
            border: "1px solid var(--color-line)",
            borderRadius: "var(--radius-card)",
          }}
        >
          <StagePanel stage={stage} disabled={!file} health={health} />
          <button
            type="button"
            disabled={!file || stage !== "idle" || health.state === "unconfigured"}
            onClick={handleAnalyze}
            className="px-6 py-3 text-base font-medium transition-opacity"
            style={{
              background: file && stage === "idle" ? "var(--color-ink)" : "var(--color-line-strong)",
              color: "var(--color-paper)",
              borderRadius: "var(--radius-button)",
              opacity: stage !== "idle" ? 0.7 : 1,
              cursor: !file || stage !== "idle" ? "not-allowed" : "pointer",
              minWidth: 220,
            }}
          >
            {stage === "idle" ? "Analyze breath sounds" : stageLabel(stage)}
          </button>
        </div>
      </section>

      {/* Result */}
      {result ? (
        <section>
          <p className="eyebrow mb-3">Step 3 · Result</p>
          <ResultCard result={result} />
        </section>
      ) : null}

      {/* Recent history */}
      {history.length > 1 ? (
        <section>
          <p className="eyebrow mb-4">Recent in this session</p>
          <ul className="space-y-2">
            {history.slice(1).map((h) => (
              <li
                key={h.timestamp}
                className="flex items-center justify-between p-4 text-sm"
                style={{
                  background: "var(--color-paper)",
                  border: "1px solid var(--color-line)",
                  borderRadius: "var(--radius-card)",
                }}
              >
                <div className="flex items-center gap-4">
                  <span
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: 999,
                      background: h.abnormal ? "var(--color-severe)" : "var(--color-safe)",
                      display: "inline-block",
                    }}
                    aria-hidden="true"
                  />
                  <span style={{ color: "var(--color-ink)" }}>{h.filename}</span>
                </div>
                <span className="tabular" style={{ color: "var(--color-muted)" }}>
                  {h.abnormal ? "Abnormal" : "Normal"} · {h.latencyMs} ms
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {/* Privacy / source pane */}
      <section
        className="grid gap-8 pt-12 md:grid-cols-2"
        style={{ borderTop: "1px solid var(--color-line)" }}
      >
        <div>
          <p className="eyebrow mb-3">Privacy</p>
          <p className="text-sm leading-relaxed" style={{ color: "var(--color-ink-soft)" }}>
            The clinic server runs on hardware you control. Malaika never
            sends recordings to a third-party cloud. The server URL is
            configured via <code style={{ color: "var(--color-muted)" }}>BREATH_API_URL</code>{" "}
            on this deployment.
          </p>
        </div>
        <div>
          <p className="eyebrow mb-3">What you are looking at</p>
          <p className="text-sm leading-relaxed" style={{ color: "var(--color-ink-soft)" }}>
            Decision support, not a diagnosis. Use this output alongside a
            full IMCI assessment. For severity-driven action, follow the
            phone&rsquo;s deterministic WHO classification.
          </p>
        </div>
      </section>
    </div>
  );
}

function stageLabel(stage: Stage): string {
  switch (stage) {
    case "uploading":
      return "Uploading...";
    case "spectrogram":
      return "Building spectrogram...";
    case "inference":
      return "Running Gemma 4...";
    case "done":
      return "Done";
    default:
      return "Analyze";
  }
}

function StagePanel({
  stage,
  disabled,
  health,
}: {
  stage: Stage;
  disabled: boolean;
  health: HealthState;
}) {
  if (health.state === "unconfigured") {
    return (
      <p className="text-xs leading-relaxed" style={{ color: "var(--color-severe)" }}>
        Set <code>BREATH_API_URL</code> on the deployment, then refresh. The
        portal works without it but cannot run analysis.
      </p>
    );
  }

  if (disabled) {
    return (
      <p className="text-xs leading-relaxed" style={{ color: "var(--color-muted)" }}>
        Pick or drop an audio file above to enable analysis.
      </p>
    );
  }

  if (stage === "idle") {
    return (
      <p className="text-xs leading-relaxed" style={{ color: "var(--color-muted)" }}>
        Audio will be converted to a mel-spectrogram on the server and
        classified by Gemma 4 E4B fine-tuned on ICBHI 2017. Typical latency
        on a Kaggle T4 is 3-5 seconds.
      </p>
    );
  }

  const steps: Array<{ key: Stage; label: string }> = [
    { key: "uploading", label: "Upload" },
    { key: "spectrogram", label: "Spectrogram" },
    { key: "inference", label: "Inference" },
  ];
  const activeIndex = steps.findIndex((s) => s.key === stage);

  return (
    <ol className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs">
      {steps.map((s, i) => {
        const done = i < activeIndex;
        const active = i === activeIndex;
        return (
          <li key={s.key} className="flex items-center gap-2 tabular">
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: 999,
                background: done
                  ? "var(--color-safe)"
                  : active
                  ? "var(--color-amber-deep)"
                  : "var(--color-line-strong)",
                display: "inline-block",
              }}
              aria-hidden="true"
            />
            <span
              style={{
                color: done || active ? "var(--color-ink)" : "var(--color-muted)",
              }}
            >
              {s.label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

function ConnectionBanner({
  health,
  onRefresh,
}: {
  health: HealthState;
  onRefresh: () => void;
}) {
  const visual = (() => {
    switch (health.state) {
      case "checking":
        return {
          dot: "var(--color-line-strong)",
          label: "Checking clinic server...",
          detail: null as string | null,
        };
      case "ready":
        return {
          dot: "var(--color-safe)",
          label: "Clinic server reachable",
          detail: `${health.model ?? "Gemma 4"} · health probe ${health.latencyMs} ms`,
        };
      case "unconfigured":
        return {
          dot: "var(--color-warning)",
          label: "Clinic server not configured",
          detail: health.message,
        };
      case "down":
        return {
          dot: "var(--color-severe)",
          label: "Clinic server unreachable",
          detail: health.message,
        };
    }
  })();

  return (
    <div
      className="flex flex-wrap items-center justify-between gap-4 p-4"
      style={{
        background: "var(--color-paper)",
        border: "1px solid var(--color-line)",
        borderRadius: "var(--radius-card)",
      }}
      role="status"
      aria-live="polite"
    >
      <div className="flex items-center gap-3">
        <span
          style={{
            width: 10,
            height: 10,
            borderRadius: 999,
            background: visual.dot,
            display: "inline-block",
            boxShadow: `0 0 0 3px color-mix(in oklch, ${visual.dot} 18%, transparent)`,
          }}
          aria-hidden="true"
        />
        <div>
          <p className="text-sm font-medium" style={{ color: "var(--color-ink)" }}>
            {visual.label}
          </p>
          {visual.detail ? (
            <p className="text-xs tabular" style={{ color: "var(--color-muted)" }}>
              {visual.detail}
            </p>
          ) : null}
        </div>
      </div>
      <button
        type="button"
        onClick={onRefresh}
        className="text-xs link-underline tabular"
        style={{ color: "var(--color-ink-soft)" }}
      >
        Re-check
      </button>
    </div>
  );
}

function ModeTabs({
  mode,
  disabled,
  onChange,
}: {
  mode: InputMode;
  disabled: boolean;
  onChange: (m: InputMode) => void;
}) {
  const tabs: Array<{ key: InputMode; label: string }> = [
    { key: "upload", label: "Upload file" },
    { key: "record", label: "Record audio" },
  ];
  return (
    <div
      role="tablist"
      aria-label="Audio source"
      className="flex"
      style={{
        background: "var(--color-paper)",
        border: "1px solid var(--color-line)",
        borderRadius: "var(--radius-button)",
        padding: 2,
      }}
    >
      {tabs.map((t) => {
        const active = mode === t.key;
        return (
          <button
            key={t.key}
            type="button"
            role="tab"
            aria-selected={active}
            disabled={disabled}
            onClick={() => onChange(t.key)}
            className="px-3 py-1.5 text-sm font-medium transition-colors"
            style={{
              background: active ? "var(--color-ink)" : "transparent",
              color: active ? "var(--color-paper)" : "var(--color-ink-soft)",
              borderRadius: "calc(var(--radius-button) - 1px)",
              cursor: disabled ? "not-allowed" : "pointer",
              opacity: disabled ? 0.5 : 1,
            }}
          >
            {t.label}
          </button>
        );
      })}
    </div>
  );
}

function RecorderPanel({
  recorder,
  file,
  onStart,
  onStop,
  onClear,
}: {
  recorder: RecorderState;
  file: File | null;
  onStart: () => void;
  onStop: () => void;
  onClear: () => void;
}) {
  const isRecording = recorder.state === "recording";
  const seconds = isRecording ? recorder.seconds : 0;
  const remaining = MAX_RECORDING_SECONDS - seconds;
  const ringPct = (seconds / MAX_RECORDING_SECONDS) * 100;
  const isRecorded = !!file && file.name.startsWith("recording-");

  return (
    <div
      className="p-10 md:p-14"
      style={{
        background: "var(--color-paper)",
        border: "1px solid var(--color-line-strong)",
        borderRadius: "var(--radius-card)",
      }}
    >
      <div className="flex flex-col items-center gap-6 text-center">
        <button
          type="button"
          onClick={isRecording ? onStop : onStart}
          disabled={recorder.state === "encoding" || recorder.state === "requesting"}
          aria-label={isRecording ? "Stop recording" : "Start recording"}
          className="relative grid place-items-center transition-transform"
          style={{
            width: 96,
            height: 96,
            borderRadius: 999,
            background: isRecording ? "var(--color-paper)" : "var(--color-ink)",
            color: isRecording ? "var(--color-severe)" : "var(--color-paper)",
            border: isRecording
              ? "1px solid var(--color-severe)"
              : "1px solid var(--color-ink)",
            cursor:
              recorder.state === "encoding" || recorder.state === "requesting"
                ? "wait"
                : "pointer",
            boxShadow: isRecording
              ? "0 0 0 6px color-mix(in oklch, var(--color-severe) 12%, transparent)"
              : "0 1px 0 rgba(0,0,0,0.06)",
          }}
        >
          {isRecording ? (
            <span
              aria-hidden="true"
              style={{
                width: 22,
                height: 22,
                background: "var(--color-severe)",
                borderRadius: 3,
              }}
            />
          ) : (
            <span
              aria-hidden="true"
              style={{
                width: 22,
                height: 22,
                background: "currentColor",
                borderRadius: 999,
              }}
            />
          )}
          {isRecording ? (
            <svg
              viewBox="0 0 100 100"
              className="absolute inset-0"
              aria-hidden="true"
              style={{ transform: "rotate(-90deg)" }}
            >
              <circle
                cx="50"
                cy="50"
                r="46"
                fill="none"
                stroke="var(--color-severe)"
                strokeWidth="2"
                strokeDasharray={`${ringPct * 2.89} 1000`}
                style={{ transition: "stroke-dasharray 250ms linear" }}
              />
            </svg>
          ) : null}
        </button>

        <div>
          {recorder.state === "idle" && !isRecorded ? (
            <>
              <p className="font-display text-xl" style={{ color: "var(--color-ink)" }}>
                Tap to start recording
              </p>
              <p
                className="mt-2 text-sm leading-relaxed"
                style={{ color: "var(--color-muted)", maxWidth: 480 }}
              >
                Hold a stethoscope to the device microphone, or rest the
                phone on the child&rsquo;s chest. Up to {MAX_RECORDING_SECONDS} seconds.
                The recording is converted to WAV in your browser before it
                leaves the page.
              </p>
            </>
          ) : null}

          {recorder.state === "requesting" ? (
            <p className="text-sm" style={{ color: "var(--color-ink-soft)" }}>
              Requesting microphone permission…
            </p>
          ) : null}

          {isRecording ? (
            <>
              <p
                className="font-display tabular"
                style={{ fontSize: "2.5rem", color: "var(--color-ink)", lineHeight: 1 }}
              >
                {formatSeconds(seconds)}
              </p>
              <p className="mt-3 text-sm tabular" style={{ color: "var(--color-muted)" }}>
                {remaining > 0
                  ? `${remaining}s remaining · tap to stop`
                  : "Stopping…"}
              </p>
            </>
          ) : null}

          {recorder.state === "encoding" ? (
            <p className="text-sm" style={{ color: "var(--color-ink-soft)" }}>
              Encoding to WAV…
            </p>
          ) : null}

          {recorder.state === "error" ? (
            <p
              role="alert"
              className="text-sm leading-relaxed"
              style={{ color: "var(--color-severe)", maxWidth: 480 }}
            >
              {recorder.message}
            </p>
          ) : null}

          {recorder.state === "idle" && isRecorded ? (
            <>
              <p className="font-display text-xl" style={{ color: "var(--color-ink)" }}>
                Recording captured
              </p>
              <p className="mt-2 text-sm tabular" style={{ color: "var(--color-muted)" }}>
                {file ? `${(file.size / 1024 / 1024).toFixed(2)} MB · WAV (PCM 16-bit, ${TARGET_SAMPLE_RATE} Hz)` : ""}
              </p>
              <div className="mt-4 flex flex-wrap items-center justify-center gap-4 text-sm">
                <button
                  type="button"
                  onClick={onStart}
                  className="link-underline"
                  style={{ color: "var(--color-ink-soft)" }}
                >
                  Record again
                </button>
                <button
                  type="button"
                  onClick={onClear}
                  className="link-underline"
                  style={{ color: "var(--color-muted)" }}
                >
                  Clear
                </button>
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function formatSeconds(s: number): string {
  const mm = Math.floor(s / 60);
  const ss = s % 60;
  return `${mm.toString().padStart(2, "0")}:${ss.toString().padStart(2, "0")}`;
}

// Decode any browser-recorded blob (WebM/Opus, MP4/AAC, etc.) and re-encode as
// a clean PCM 16-bit mono WAV at the sample rate the librosa pipeline expects.
// Keeping the encoding in the browser means the notebook /breath endpoint
// stays unchanged and accepts the file like any other .wav upload.
async function encodeBlobAsWav(blob: Blob): Promise<File> {
  const arrayBuffer = await blob.arrayBuffer();
  const AudioCtx: typeof AudioContext =
    window.AudioContext ||
    (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
  // Decode at native rate first; we'll resample by sampling the channelData.
  const decodeCtx = new AudioCtx();
  const decoded = await decodeCtx.decodeAudioData(arrayBuffer.slice(0));
  await decodeCtx.close();

  // Resample to TARGET_SAMPLE_RATE via OfflineAudioContext for clean output
  const offline = new OfflineAudioContext(1, Math.ceil(decoded.duration * TARGET_SAMPLE_RATE), TARGET_SAMPLE_RATE);
  const src = offline.createBufferSource();
  src.buffer = decoded;
  src.connect(offline.destination);
  src.start();
  const rendered = await offline.startRendering();

  const wavBlob = bufferToWav(rendered);
  const filename = `recording-${new Date().toISOString().replace(/[:.]/g, "-")}.wav`;
  return new File([wavBlob], filename, { type: "audio/wav" });
}

function bufferToWav(buffer: AudioBuffer): Blob {
  const numChannels = 1;
  const sampleRate = buffer.sampleRate;
  const bytesPerSample = 2;
  const data = buffer.getChannelData(0);
  const dataLength = data.length * numChannels * bytesPerSample;

  const ab = new ArrayBuffer(44 + dataLength);
  const view = new DataView(ab);
  let offset = 0;

  function writeStr(s: string) {
    for (let i = 0; i < s.length; i++) view.setUint8(offset + i, s.charCodeAt(i));
    offset += s.length;
  }

  writeStr("RIFF");
  view.setUint32(offset, 36 + dataLength, true); offset += 4;
  writeStr("WAVE");
  writeStr("fmt ");
  view.setUint32(offset, 16, true); offset += 4;            // PCM chunk size
  view.setUint16(offset, 1, true); offset += 2;             // format = 1 (PCM)
  view.setUint16(offset, numChannels, true); offset += 2;
  view.setUint32(offset, sampleRate, true); offset += 4;
  view.setUint32(offset, sampleRate * numChannels * bytesPerSample, true); offset += 4;
  view.setUint16(offset, numChannels * bytesPerSample, true); offset += 2;
  view.setUint16(offset, 16, true); offset += 2;            // bits per sample
  writeStr("data");
  view.setUint32(offset, dataLength, true); offset += 4;

  for (let i = 0; i < data.length; i++) {
    const s = Math.max(-1, Math.min(1, data[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    offset += 2;
  }

  return new Blob([ab], { type: "audio/wav" });
}

function SampleHint() {
  return (
    <div
      className="mt-5 p-5 text-sm leading-relaxed"
      style={{
        background: "color-mix(in oklch, var(--color-amber-soft) 60%, transparent)",
        border: "1px solid var(--color-amber-soft)",
        borderRadius: "var(--radius-card)",
        color: "var(--color-ink-soft)",
      }}
    >
      <p className="eyebrow mb-2" style={{ color: "var(--color-amber-deep)" }}>
        Need a sample to test with?
      </p>
      <p>
        Use any 10-30 second recording of a child&rsquo;s breathing. For
        reproducible benchmarking, the model was trained on the{" "}
        <a
          href="https://bhichallenge.med.auth.gr/ICBHI_2017_Challenge"
          target="_blank"
          rel="noreferrer"
          className="link-underline"
          style={{ color: "var(--color-amber-deep)" }}
        >
          ICBHI 2017 respiratory sound dataset
        </a>
        . Notebook 06 in the repository documents the patient-level held-out
        split &mdash; any of those WAV files will work end-to-end here.
      </p>
    </div>
  );
}

function ResultCard({ result }: { result: AnalysisResult }) {
  if (!result.ok) {
    return (
      <div
        role="alert"
        className="p-8"
        style={{
          background: "var(--color-paper)",
          border: "1px solid var(--color-severe)",
          borderRadius: "var(--radius-card)",
        }}
      >
        <p className="eyebrow mb-2" style={{ color: "var(--color-severe)" }}>
          Analysis failed
        </p>
        <p className="text-base" style={{ color: "var(--color-ink)" }}>
          {result.error}
        </p>
        <p className="mt-4 text-sm" style={{ color: "var(--color-muted)" }}>
          Common causes: <code>BREATH_API_URL</code> not set, notebook 12
          session expired, or the ngrok tunnel was rotated. Re-check
          connection and try again.
        </p>
      </div>
    );
  }

  const accentColor = result.abnormal ? "var(--color-severe)" : "var(--color-safe)";
  const headline = result.abnormal
    ? "Abnormal breath sounds detected"
    : "Breath sounds appear normal";
  const confidence =
    typeof result.confidence === "number"
      ? `${Math.round(result.confidence * 100)}% model confidence`
      : "Confidence not reported";

  return (
    <article
      className="p-10 md:p-12"
      style={{
        background: "var(--color-paper)",
        boxShadow: "var(--shadow-card)",
        borderRadius: "var(--radius-card)",
        borderLeft: `3px solid ${accentColor}`,
      }}
    >
      <p className="eyebrow mb-4" style={{ color: accentColor }}>
        Result
      </p>
      <h3
        className="font-display"
        style={{ fontSize: "clamp(1.75rem, 3vw, 2.5rem)", color: "var(--color-ink)" }}
      >
        {headline}
      </h3>

      <dl className="mt-10 grid gap-6 md:grid-cols-3">
        <div style={{ borderTop: "1px solid var(--color-line)", paddingTop: "1rem" }}>
          <dt className="eyebrow">Confidence</dt>
          <dd className="mt-2 text-base tabular" style={{ color: "var(--color-ink)" }}>
            {confidence}
          </dd>
        </div>
        <div style={{ borderTop: "1px solid var(--color-line)", paddingTop: "1rem" }}>
          <dt className="eyebrow">Latency</dt>
          <dd className="mt-2 text-base tabular" style={{ color: "var(--color-ink)" }}>
            {result.latencyMs} ms
          </dd>
        </div>
        <div style={{ borderTop: "1px solid var(--color-line)", paddingTop: "1rem" }}>
          <dt className="eyebrow">File</dt>
          <dd
            className="mt-2 text-base"
            style={{ color: "var(--color-ink)", wordBreak: "break-all" }}
          >
            {result.filename}
          </dd>
        </div>
      </dl>

      {/* THE CENTERPIECE — Gemma 4's clinical reasoning, written in a senior-nurse voice. */}
      {result.clinicalNote ? (
        <figure
          className="mt-12"
          style={{
            borderLeft: `2px solid ${accentColor}`,
            paddingLeft: "clamp(1.25rem, 2.5vw, 2rem)",
          }}
        >
          <figcaption className="eyebrow mb-4" style={{ color: accentColor }}>
            Clinical note · Malaika
          </figcaption>
          <blockquote
            className="font-display"
            style={{
              fontSize: "clamp(1.125rem, 1.5vw, 1.375rem)",
              lineHeight: 1.55,
              color: "var(--color-ink)",
              fontStyle: "italic",
              fontWeight: 400,
              letterSpacing: "-0.005em",
              margin: 0,
            }}
          >
            {result.clinicalNote}
          </blockquote>
          <p
            className="mt-5 text-xs"
            style={{ color: "var(--color-muted)", letterSpacing: "0.02em" }}
          >
            &mdash; Generated by Gemma 4 from the auscultation finding.
            Decision support for your chart entry; review before signing.
          </p>
        </figure>
      ) : null}

      {result.clinicalNoteError ? (
        <div
          className="mt-10 p-4 text-sm"
          style={{
            background: "color-mix(in oklch, var(--color-warning) 8%, transparent)",
            borderRadius: "var(--radius-card)",
            color: "var(--color-ink-soft)",
          }}
        >
          <p className="eyebrow mb-1" style={{ color: "var(--color-warning)" }}>
            Clinical note unavailable
          </p>
          <p>The classification succeeded, but the reasoning pass failed: {result.clinicalNoteError}</p>
        </div>
      ) : null}

      {result.description ? (
        <details className="mt-10" style={{ borderTop: "1px solid var(--color-line)", paddingTop: "1rem" }}>
          <summary
            className="eyebrow cursor-pointer select-none"
            style={{ listStyle: "none" }}
          >
            Model technical description
          </summary>
          <p className="mt-3 text-sm leading-relaxed" style={{ color: "var(--color-ink-soft)" }}>
            {result.description}
          </p>
        </details>
      ) : null}

      {/* Clinical context — turns "abnormal: true" into something usable. */}
      <div
        className="mt-10 p-6"
        style={{
          background: result.abnormal
            ? "color-mix(in oklch, var(--color-severe) 6%, transparent)"
            : "color-mix(in oklch, var(--color-safe) 6%, transparent)",
          borderRadius: "var(--radius-card)",
        }}
      >
        <p className="eyebrow mb-3" style={{ color: accentColor }}>
          What this means
        </p>
        {result.abnormal ? (
          <ul className="space-y-2 text-sm leading-relaxed" style={{ color: "var(--color-ink-soft)" }}>
            <li>
              The model detected adventitious breath sounds &mdash; wheeze,
              crackles, or stridor &mdash; consistent with a lower respiratory
              tract sign.
            </li>
            <li>
              <strong style={{ color: "var(--color-ink)" }}>Action:</strong> in
              the WHO IMCI flow, this is a finding to combine with respiratory
              rate, chest indrawing, and danger signs before classifying.
              Severity is determined by the deterministic phone-side classifier,
              not by this model.
            </li>
            <li>
              If chest indrawing or any general danger sign is also present
              &mdash; classify as <strong style={{ color: "var(--color-severe)" }}>severe pneumonia</strong>{" "}
              and refer urgently.
            </li>
          </ul>
        ) : (
          <ul className="space-y-2 text-sm leading-relaxed" style={{ color: "var(--color-ink-soft)" }}>
            <li>
              The model did not detect adventitious sounds in this recording.
              Air entry sounds within normal limits.
            </li>
            <li>
              <strong style={{ color: "var(--color-ink)" }}>Action:</strong> a
              normal breath-sound result does not rule out pneumonia. Continue
              the IMCI assessment &mdash; check respiratory rate, chest
              indrawing, fever, and danger signs before classifying.
            </li>
            <li>
              Re-record and re-assess if the recording was short, noisy, or
              contained crying that could mask abnormal sounds.
            </li>
          </ul>
        )}
      </div>

      <div
        className="mt-8 grid gap-4 pt-6 text-xs md:grid-cols-2"
        style={{ borderTop: "1px solid var(--color-line)", color: "var(--color-muted)" }}
      >
        <p>Model: Gemma 4 E4B + LoRA on ICBHI 2017</p>
        <p className="md:text-right">
          Held-out crackle detection: 85% &middot; notebook 06
        </p>
      </div>
    </article>
  );
}
