# observability/ — Observability Skill

> If you can't see what happened, you can't fix it, prove it, or improve it.

---

## What This Module Does

Records everything that happens during an IMCI assessment for three audiences:

1. **Developers**: Debug why a classification was wrong — see exact inputs, prompts, outputs
2. **Evaluators**: Prove accuracy — 20+ scenarios with traced evidence for the writeup
3. **Prompt engineers**: Improve prompts — link corrections to specific traces

This module provides:
- **Step tracing** (`tracer.py`): Per-IMCI-step record of what happened
- **Cost tracking** (`cost_tracker.py`): Token counts, latency, VRAM per call
- **Feedback linking** (`feedback.py`): Connect corrections to traces for improvement

## What This Module Does NOT Do

- Does NOT make clinical decisions (that's `imci_protocol.py`)
- Does NOT validate output (that's `guards/output_validator.py`)
- Does NOT store media files (traces store hashes, never raw data)
- Does NOT send data anywhere (offline-only, local files)

---

## Rules

### R1: Trace Every Inference Call
Every call to `inference.py` produces a `StepTrace`. No exceptions. This is automatic — the tracer is called by the IMCI engine, not by individual modules.

### R2: Never Store Raw Media in Traces
Traces store:
- Input hash (SHA-256 of the file) — NOT the file itself
- Raw model output (truncated to `max_raw_output_length`) — text only
- Parsed result (string representation)
- Prompt name and version used

Never: file paths with usernames, raw images, audio recordings, video data.

### R3: Truncate Raw Output
Model output in traces is truncated to `config.observability.max_raw_output_length` (default 500 chars). Enough to debug, not enough to reconstruct patient data.

### R4: Cost Tracking is Per-Call AND Per-Assessment
Track both:
- **Per-call**: tokens_in, tokens_out, latency_ms, cache_hit
- **Per-assessment**: total_tokens, total_latency_ms, step_count, retries_count

This feeds into performance budget enforcement (TESTING_STRATEGY.md benchmarks).

### R5: Traces Are JSON-Serializable
`AssessmentTrace` must be serializable to JSON for:
- Export as evaluation evidence (writeup)
- Comparison across prompt versions
- Aggregation for accuracy reports

### R6: Feedback Links Are Specific
When someone corrects a result ("this was actually normal breathing, not fast"), the correction links to a specific `StepTrace` by `session_id + step_index`. This creates training data for prompt improvement.

### R7: Traces Are Ephemeral By Default
Traces are saved to `traces/` directory only when explicitly requested (e.g., during evaluation runs). In normal operation, traces live in memory for the session and are discarded. No patient data persists.

---

## Trace Format

```json
{
  "session_id": "abc123",
  "started_at": "2026-04-12T18:30:00Z",
  "steps": [
    {
      "imci_state": "BREATHING",
      "prompt_name": "breathing.count_rate_from_video",
      "prompt_version": "1.0.0",
      "input_hash": "sha256:a1b2c3...",
      "raw_output": "{\"breath_count\": 12, \"confidence\": 0.85, ...}",
      "parsed_result": "BreathingRateResult(breath_count=12, rate=48)",
      "confidence": 0.85,
      "latency_ms": 3200,
      "tokens_in": 1024,
      "tokens_out": 45,
      "retries": 0,
      "cache_hit": false
    }
  ],
  "total_tokens": 8500,
  "total_latency_ms": 45000
}
```

---

## File Inventory

| File | Component | Responsibility |
|------|-----------|----------------|
| `__init__.py` | Module | Exports `Tracer`, `CostTracker`, `FeedbackCollector` |
| `tracer.py` | Step Tracer | `StepTrace` creation, `AssessmentTrace` aggregation, JSON export |
| `cost_tracker.py` | Cost Tracker | Token counting, latency recording, VRAM snapshots, budget alerts |
| `feedback.py` | Feedback | Link corrections to traces, export correction pairs |
