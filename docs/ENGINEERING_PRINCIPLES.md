# Malaika — Engineering Principles

> These principles govern every line of code. When in doubt, refer here.

---

## 1. Core Principles

### P1: Offline is Non-Negotiable

Every feature, every dependency, every interaction must work with zero internet connectivity. This is not a "nice to have" — it is the core value proposition. A mother at 2am in rural Kenya has no WiFi.

**In practice:**
- No HTTP calls in any production code path
- No CDN-loaded assets in the UI
- No API keys, no cloud services, no remote model endpoints
- All model weights are local files
- TTS voices are pre-downloaded
- Test offline by disabling network: `export NO_PROXY=* && unset http_proxy https_proxy`

### P2: Gemma 4 is the Intelligence — Code is the Logic

Gemma 4 handles perception (seeing, hearing, understanding language). Code handles decisions (WHO thresholds, state transitions, classifications). This boundary is absolute.

**In practice:**
- Never ask Gemma 4 to make a clinical classification — that's deterministic code
- Never hardcode visual recognition — that's Gemma 4's job
- `imci_protocol.py` MUST NOT import `inference.py`
- `inference.py` MUST NOT contain any clinical thresholds

### P3: Fail Safe, Not Fail Silent

When something goes wrong, the system must remain safe for the child. An uncertain AI result is not a classification — it's a prompt to seek human help.

**In practice:**
- Unknown or low-confidence AI perception -> "UNCERTAIN" finding, not a guess
- Any danger sign detected -> always escalate to URGENT regardless of confidence
- Parsing failure from Gemma 4 -> return structured `Uncertain` result, never crash
- If in doubt, recommend referral — false positive (unnecessary clinic visit) is safer than false negative (missed danger sign)

### P4: Modular and Pluggable

Each capability (vision, audio, heart MEMS, TTS, multilingual) is an independent module. Disabling any module must not break the assessment flow.

**In practice:**
- Feature flags in `config.py` for every optional module
- `if not config.ENABLE_HEART_RATE: skip` — zero code changes needed
- Each module has its own test file
- IMCI engine handles missing modules gracefully (records "not assessed")

### P5: Deterministic Where Possible

Randomness is the enemy of medical safety. Wherever the system can be deterministic, it must be.

**In practice:**
- WHO thresholds are constants, not model outputs
- IMCI state machine transitions are explicit, not LLM-decided
- Same clinical findings -> same classification, every time
- Model temperature=0.0 for clinical assessments (factual, not creative)
- Set random seeds for reproducible testing

---

## 2. Code Quality Standards

### Typing

All public functions and methods MUST have complete type annotations. Use `mypy --strict`.

```python
# YES
def classify_breathing(rate: int, age_months: int) -> BreathingClassification:
    ...

# NO
def classify_breathing(rate, age_months):
    ...
```

### Naming

- Classes: `PascalCase` — `IMCIEngine`, `MalaikaInference`, `BreathingAssessment`
- Functions/methods: `snake_case` — `analyze_image`, `classify_danger_signs`
- Constants: `UPPER_SNAKE_CASE` — `BREATHING_THRESHOLD_2_TO_11_MONTHS`
- Private: Leading underscore — `_parse_gemma_response`, `_transition_state`
- Files: `snake_case.py` — `imci_engine.py`, `imci_protocol.py`
- Tests: `test_<module>.py` — `test_imci_engine.py`

### Imports

```python
# Standard library
import os
from pathlib import Path
from enum import Enum

# Third party
import torch
import gradio as gr

# Local
from malaika.inference import MalaikaInference
from malaika.types import AssessmentResult
```

Always absolute imports. Never `from malaika import *`.

### Docstrings

Google style. Required on all public classes and functions. Not required on private helpers if the name is self-explanatory.

```python
def analyze_chest_image(image_path: Path, inference: MalaikaInference) -> ChestAssessment:
    """Analyze a chest image for indrawing and respiratory distress signs.

    Uses Gemma 4 vision to detect subcostal/intercostal indrawing
    and visible signs of respiratory distress.

    Args:
        image_path: Path to the chest image file (JPEG/PNG).
        inference: Loaded MalaikaInference instance.

    Returns:
        ChestAssessment with indrawing detection and confidence score.

    Raises:
        FileNotFoundError: If image_path does not exist.
        ModelError: If Gemma 4 inference fails.
    """
```

---

## 3. Error Handling Philosophy

### Hierarchy of Error Response

1. **Self-correct** — Parse failure? Retry with correction prompt (max 2 retries). See ARCHITECTURE.md 4.9.
2. **Recover and continue** — Still can't parse? Return `Uncertain`. Assessment continues.
3. **Degrade gracefully** — Module unavailable? Skip it, note "not assessed."
4. **Fail with context** — Unrecoverable? Raise typed exception with clear message.
5. **Never crash silently** — Every error is logged with `structlog`. Every retry is traced.

### Typed Exceptions

```python
class MalaikaError(Exception):
    """Base exception for all Malaika errors."""

class ModelError(MalaikaError):
    """Gemma 4 inference failed (OOM, load failure, generation error)."""

class PerceptionError(MalaikaError):
    """AI perception succeeded but output couldn't be parsed."""

class ProtocolError(MalaikaError):
    """IMCI protocol violation (invalid state transition, missing data)."""

class InputValidationError(MalaikaError):
    """User input failed validation (wrong format, too large, corrupt)."""
```

### What NOT to Catch

- Don't catch `KeyboardInterrupt` or `SystemExit`
- Don't catch generic `Exception` except at the top-level UI boundary
- Don't suppress errors that indicate programmer mistakes (`TypeError`, `AttributeError`)

---

## 4. Performance Principles

### Model Loading
- Load Gemma 4 ONCE at startup. Never reload mid-session.
- Use 4-bit quantization by default (BitsAndBytes).
- Lazy-load optional modules (TTS, video processing) — don't pay for what you don't use.

### Inference Optimization
- Batch related prompts when possible (but don't compromise clarity).
- Set `max_new_tokens` appropriately per task — breathing rate needs 50 tokens, not 512.
- Use `torch.inference_mode()` context manager for all inference calls.
- Use response cache for identical inputs — don't re-analyze the same image twice.
- Track token count and latency per call via `cost_tracker` for budget enforcement.

### Memory Management
- Monitor VRAM usage — log it at startup and after model load.
- Clear CUDA cache between heavy operations if needed.
- Never load two models simultaneously.

### UI Responsiveness
- Show progress indicators during inference ("Malaika is analyzing...").
- Stream long text responses where Gradio supports it.
- Pre-warm the model with a dummy inference at startup (hidden from user).

---

## 5. Logging Standards

Use `structlog` for all logging. Structured, machine-parseable, human-readable.

```python
import structlog

logger = structlog.get_logger()

# Good: structured context
logger.info("imci_state_transition", from_state="BREATHING", to_state="DIARRHEA",
            findings_count=3)

# Good: error with context
logger.error("perception_parse_failed", module="vision", raw_output=raw[:200],
             expected_type="ChestAssessment")

# Bad: unstructured string
logger.info(f"Moving from {state1} to {state2}")
```

### Log Levels
- `DEBUG`: Model input/output (truncated), intermediate parsing steps
- `INFO`: State transitions, assessment milestones, module load/unload
- `WARNING`: Low confidence results, fallback paths taken, degraded operation
- `ERROR`: Parse failures, model errors, input validation failures
- `CRITICAL`: Model failed to load, unrecoverable state

---

## 6. Dependency Principles

### Adding Dependencies

Before adding any dependency, answer:
1. Does it work offline? (Must be YES)
2. Is it necessary, or can we do this in <20 lines of code? (Prefer fewer deps)
3. Is it actively maintained? (Check last commit date)
4. Does it have a compatible license? (Apache 2.0, MIT, BSD preferred)
5. Does it add significant binary size? (Matters for deployment)

### Pinning

All dependencies pinned to exact versions in `requirements.txt`. No ranges, no `>=`.

```
# YES
transformers==4.52.0
torch==2.6.0

# NO
transformers>=4.50
torch
```

### Separation of Concerns

- `requirements.txt` — Runtime dependencies (inference, UI, TTS)
- `requirements-dev.txt` — Development tools (pytest, mypy, ruff)
- `requirements-train.txt` — Training only (unsloth, trl, datasets)

---

## 7. Configuration Principles

### No Magic Numbers

Every threshold, timeout, path, and parameter must be a named constant or config value.

```python
# YES — in imci_protocol.py
FAST_BREATHING_THRESHOLD_2_TO_11_MONTHS: int = 50  # breaths/min, WHO IMCI Chart Booklet p.5
FAST_BREATHING_THRESHOLD_12_TO_59_MONTHS: int = 40

# NO — buried in logic
if rate >= 50:
    ...
```

### Single Source of Truth

- Clinical thresholds: `imci_protocol.py`
- Feature flags: `config.py` (loaded from `configs/features.yaml`)
- Model paths: `config.py`
- Audio/video parameters: `config.py`

Never duplicate a constant. Import it.
