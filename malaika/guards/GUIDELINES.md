# guards/ — Security Guard Skill

> Three guards. Every call. No exceptions. Input -> Content -> Output.

---

## What This Module Does

Implements a three-layer security pipeline that wraps every AI perception call:

1. **Input Guard** (`input_guard.py`): Validates files BEFORE they reach the model
2. **Content Filter** (`content_filter.py`): Sanitizes text and wraps prompts BEFORE inference
3. **Output Validator** (`output_validator.py`): Validates model output BEFORE it enters clinical logic

The guard pipeline runs in strict order. If any guard rejects, the call stops.

## What This Module Does NOT Do

- Does NOT call inference (that's `inference.py`)
- Does NOT make clinical decisions (that's `imci_protocol.py`)
- Does NOT define prompts (that's `prompts/`)
- Does NOT log/trace (that's `observability/`)

---

## The Pipeline

```
User Input
    │
    ▼
┌──────────────────┐
│  INPUT GUARD      │  File exists? Right format? Under size limit?
│                   │  No path traversal? No symlinks?
│  Rejects: bad     │
│  files, oversized │  Output: ValidatedInput or InputValidationError
│  corrupt media    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  CONTENT FILTER   │  Text sanitized? Null bytes stripped?
│                   │  Prompt wrapped in injection-safe boundary?
│  Prevents: prompt │  PII markers scrubbed?
│  injection, PII   │
│  leakage          │  Output: SafePrompt (ready for inference)
└────────┬─────────┘
         │
         ▼
    [ INFERENCE ]    (not part of guards — handled by inference.py)
         │
         ▼
┌──────────────────┐
│  OUTPUT VALIDATOR │  Valid JSON? Matches schema? Values plausible?
│                   │  Confidence above threshold?
│  Catches: garbled │
│  output, halluc.  │  Output: ValidatedOutput or triggers self-correction
│  implausible vals │
└──────────────────┘
```

---

## Rules

### R1: Guards Are Non-Negotiable
Every perception call (vision, audio, video) MUST pass through all three guards. No shortcuts. No "just this once" bypasses.

### R2: Input Guard Validates By Magic Bytes
NEVER trust file extensions. A file named `photo.jpg` could be anything. Read the first bytes to detect actual format.

```python
# CORRECT
actual_format = identify_format_by_magic_bytes(file_path)

# WRONG
if file_path.suffix == ".jpg":
```

### R3: Content Filter Wraps, Never Modifies Clinical Intent
The content filter adds safety boundaries around user text but NEVER changes the clinical question being asked. It's a wrapper, not a rewriter.

### R4: Output Validator Checks Physiological Plausibility
A breathing rate of 500/min is not just a parsing error — it's a safety hazard. Validate ranges:

| Field | Plausible Range | Source |
|-------|----------------|--------|
| `breath_count` (15s video) | 0-30 | Max 120/min = 30 per 15s |
| `breathing_rate` (per min) | 5-120 | Neonates max ~80, distressed up to ~120 |
| `heart_rate` (BPM) | 60-220 | Pediatric range |
| `confidence` | 0.0-1.0 | By definition |
| `muac_mm` | 50-250 | Physical arm circumference range |

### R5: Failed Output Triggers Self-Correction, Not Crash
When output_validator rejects model output:
1. First rejection -> retry with correction prompt (inference.py handles this)
2. Second rejection -> retry with simplified prompt
3. Third rejection -> return `ValidatedOutput(status="uncertain")`

The guard signals the failure. Inference.py executes the retry. Clean separation.

### R6: Never Log PII
Guards see raw user input. NEVER log:
- File paths containing usernames
- Raw audio content or transcriptions
- Images or image thumbnails
- Any content that could identify the child or caregiver

Log only: file size, format detected, validation result (pass/fail), rejection reason.

---

## How to Add a New Validation Rule

1. Determine which guard layer owns it (input/content/output)
2. Add the check to the appropriate guard file
3. Add a test in `tests/test_guards.py`
4. If it's a new plausible range, add to the table above and in the code constants

---

## File Inventory

| File | Guard Layer | Responsibility |
|------|-------------|----------------|
| `__init__.py` | Pipeline | `run_input_pipeline()`, `run_output_pipeline()` |
| `input_guard.py` | Layer 1 | File validation, format detection, size limits |
| `content_filter.py` | Layer 2 | Text sanitization, prompt injection defense, PII scrub |
| `output_validator.py` | Layer 3 | JSON schema validation, plausibility checks, confidence gating |
