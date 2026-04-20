# Malaika — Project Instructions

> **Malaika** (Angel in Swahili): WHO IMCI child survival AI powered by Gemma 4, running fully offline on any phone.
> **Competition**: Google Gemma 4 Good Hackathon | **Deadline**: May 18, 2026 | **Prize target**: $70K (Main + Health + Unsloth)

---

## Absolute Rules

1. **MOBILE FIRST. The phone IS the product.** The Android app with Gemma 4 E2B is the primary demo. GPU/Colab is supplementary.
2. **EVERYTHING runs offline. No internet. No exceptions.** Every feature must work without connectivity on the phone.
3. **ALL intelligence comes from Gemma 4.** It IS the solution, not a tool we use. No other LLMs. The reason only Gemma 4 works: no other model runs on a phone with text + vision in <3GB.
4. **Every claim must be implementable ON THE PHONE.** No hand-waving. If it's in the writeup, it works on-device. Do NOT claim capabilities that only work on GPU (e.g., breath counting from video, spectrogram analysis).
5. **Medical safety first.** This is decision SUPPORT, not diagnosis. WHO IMCI thresholds are deterministic code, never LLM output.
6. **Single developer model.** No assumptions about who does what — any task can be picked up by anyone.

---

## Project Structure

```
malaika/                  # Main Python package
  __init__.py
  skills.py               # SkillRegistry — 12 clinical skills, BeliefState, SkillResult
  chat_engine.py          # Agentic IMCI conversation — orchestrates skills, emits events
  voice_app.py            # FastAPI server — REST + WebSocket voice endpoints
  voice_session.py        # Real-time voice pipeline — sentence TTS, filler audio, events
  inference.py            # MalaikaInference — single Gemma 4 model, all modalities
  imci_engine.py          # IMCI protocol state machine (deterministic, Gradio path)
  imci_protocol.py        # WHO threshold constants and classification logic
  vision.py               # Image/video analysis via Gemma 4
  audio.py                # Audio analysis (breath sounds, speech) via Gemma 4
  tts.py                  # Piper TTS output (offline text-to-speech)
  app.py                  # Gradio UI entry point (form-based)
  config.py               # Feature flags, model paths, thresholds
  types.py                # Shared type definitions (dataclasses, enums)
  utils.py                # Shared utilities (logging, file handling)
  static/
    index.html            # Voice UI — orb, skill cards, classification cards, progress bar

  prompts/                # Versioned, typed prompt templates (NEVER hardcode prompts)
    __init__.py           # PromptRegistry — central prompt discovery
    base.py               # PromptTemplate base class
    danger_signs.py       # Danger sign assessment prompts
    breathing.py          # Breathing rate + respiratory prompts
    diarrhea.py           # Diarrhea and dehydration prompts
    fever.py              # Fever assessment prompts
    nutrition.py          # Nutrition and wasting prompts
    heart.py              # Heart sounds (MEMS) prompts
    treatment.py          # Treatment generation prompts
    speech.py             # Speech understanding prompts
    system.py             # System prompts (Malaika persona)

  guards/                 # Three-layer security — input, content, output
    __init__.py           # Guard pipeline: run all three in sequence
    input_guard.py        # File validation, size limits, format checks (magic bytes)
    content_filter.py     # Prompt injection defense, PII scrubbing
    output_validator.py   # Model output schema validation, confidence gating

  observability/          # Per-stage tracing, cost tracking, feedback
    __init__.py
    tracer.py             # Per-IMCI-step trace (input, output, latency, confidence)
    cost_tracker.py       # Token count and inference time per call
    feedback.py           # Link assessment corrections to traces for prompt improvement

  evaluation/             # Golden datasets and offline evaluation
    __init__.py
    golden_scenarios.py   # 20+ WHO IMCI test scenarios with expected outcomes
    evaluator.py          # Run model against golden set, produce accuracy report

tests/                    # All tests (mirrors malaika/ structure, 104+ passing)
  test_inference.py
  test_imci_engine.py     # 26 tests — state machine, assessments, findings
  test_imci_protocol.py   # 78 tests — WHO thresholds, classifications, golden scenarios
  test_vision.py
  test_audio.py
  test_prompts.py         # Prompt rendering and parsing tests
  test_guards.py          # Input/content/output guard tests
  conftest.py             # Shared fixtures

notebooks/                # Colab notebooks for running + fine-tuning
  10_voice_agent_colab.ipynb  # Launch voice agent on Colab T4 (primary demo)
  09_chat_app_colab.ipynb     # Gradio chat app on Colab
  08_colab_run_app.ipynb      # Full app on Colab

scripts/                  # One-off scripts (data prep, benchmarks, exports)
adapters/                 # Fine-tuned LoRA adapter weights
configs/                  # YAML/JSON config files
data/                     # Datasets (gitignored, downloaded via scripts)
docs/                     # Engineering documentation (see below)

malaika_flutter/          # PRIMARY DEMO — Android app with Gemma 4 E2B
  lib/
    screens/
      splash_screen.dart        # Model download + GPU initialization
      dashboard_screen.dart     # Main menu
      home_screen.dart          # IMCI Q&A orchestrator (~970 lines)
      camera_monitor_screen.dart # Gallery photo picker + vision analysis
    core/
      imci_questionnaire.dart   # Structured IMCI questions + answer parsing
      imci_protocol.dart        # WHO thresholds + deterministic classification
      imci_types.dart           # Enums for severity, classification
      reconciliation_engine.dart # Q&A vs vision cross-reference
    theme/
      malaika_theme.dart        # Brand colors, severity colors
    widgets/
      chat_bubble.dart          # Chat UI bubbles
      imci_progress_bar.dart    # Step progress indicator
      classification_card.dart  # WHO classification display
      reasoning_card.dart       # Extracted findings display
    inference/
      model_manager.dart        # Model path management (legacy GGUF fallback)
```

---

## Engineering Documentation

Read these before writing any code. They are the law.

| Document | Purpose |
|----------|---------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture, component boundaries, data flow, deployment topology |
| [docs/ENGINEERING_PRINCIPLES.md](docs/ENGINEERING_PRINCIPLES.md) | Core design principles, error handling philosophy, performance standards |
| [docs/TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md) | Testing pyramid, coverage targets, medical accuracy validation |
| [docs/SECURITY.md](docs/SECURITY.md) | Data privacy, input validation, model safety, dependency security |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Code style, type hints, git workflow, commit conventions, env setup |
| [docs/PROMPT_ENGINEERING.md](docs/PROMPT_ENGINEERING.md) | Versioned prompt management, PromptTemplate pattern, prompt design rules |

---

## Phone App — What ACTUALLY Works (tested Apr 19, 2026)

The Flutter Android app is the PRIMARY demo. Here is exactly what it does and doesn't do:

| Feature | Status | Details |
|---------|--------|---------|
| Text-based IMCI Q&A | **WORKS** | ~20 structured questions, Gemma narrates naturally |
| Photo from gallery → vision analysis | **WORKS** | Gallery picker, Gemma checks alertness/dehydration/wasting/edema |
| Q&A vs vision reconciliation | **WORKS** | Cross-references verbal + visual findings, generates warnings |
| WHO IMCI classification | **WORKS** | Deterministic code, not LLM output |
| Final report with severity | **WORKS** | LLM summary + structured treatment actions |
| Fully offline | **WORKS** | All intelligence from on-device Gemma 4 E2B |
| In-app camera preview | **NO** | Mali GPU can't hold model + camera simultaneously |
| System camera (take photo) | **NO** | Android OOM-kills app when it backgrounds |
| Voice input/output | **NO** | Text-only on phone (voice is Python/Colab only) |
| Breathing rate from video | **NO** | No video processing on phone |
| Chest indrawing detection | **NO** | Requires motion observation, photo can't capture |
| Audio/breath sounds | **NO** | No microphone input in Flutter app |
| Real-time monitoring | **NO** | Single photo assessment, not continuous |

### GPU Memory Constraint (Samsung A53, Mali G68)
- Gemma 4 E2B uses ~2.3GB of ~2.5GB GPU
- Camera preview surfaces crash the driver (no headroom)
- Gallery picker works because it's in-process, no GPU allocation
- Fresh LLM session per inference prevents KV cache accumulation crash

---

## Quick Reference

### Models
- **Gemma 4 E4B** (4.5B active): Demo machine via Transformers. Fine-tuned with LoRA. ~5-6GB VRAM in 4-bit.
- **Gemma 4 E2B** (2.3B active): Phone via LiteRT-LM. Base model. 50+ tok/s, 2.58GB disk.

### IMCI Flow
```
START -> DANGER_SIGNS -> BREATHING -> DIARRHEA -> FEVER -> NUTRITION -> [HEART_MEMS] -> CLASSIFY -> TREAT
```

### Key Commands
```bash
# Run the voice agent (primary demo — FastAPI + voice UI)
# Requires: model loaded via Colab notebook or local GPU
# See notebooks/10_voice_agent_colab.ipynb

# Run the Gradio app (form-based UI)
python -m malaika.app

# Run tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=malaika --cov-report=term-missing

# Type checking
mypy malaika/ --strict

# Linting
ruff check malaika/ tests/
ruff format malaika/ tests/

# Run specific test module
pytest tests/test_imci_protocol.py -v
```

### Feature Flags (configs/features.yaml — Python/Colab only)
```yaml
enable_heart_rate: false    # MEMS heart module — not implemented
enable_tts: true            # Piper TTS spoken output (Colab only, not on phone)
enable_video_breathing: false # NOT IMPLEMENTED on phone — single photo only
enable_multilingual: true   # Multi-language support (model supports it)
```

---

## Production AI Patterns

These patterns elevate Malaika from hackathon code to production-grade AI:

1. **Skills-Based Agent Architecture** (`malaika/skills.py`): 12 clinical skills registered in `SkillRegistry`. Each skill has typed I/O, maps to an IMCI step, and produces structured `SkillResult` with confidence scores. `BeliefState` tracks confirmed/uncertain/pending findings. `ChatEngine` orchestrates skills and emits structured events (`skill_invoked`, `skill_result`, `classification`, `step_change`, `finding`, `image_request`, `assessment_complete`, `danger_alert`). Showcases Gemma 4's 1200% improvement in agentic tool use.

2. **Prompts as Code**: All Gemma 4 prompts are versioned `PromptTemplate` objects in `malaika/prompts/`. Never hardcode prompt strings in service logic. See [docs/PROMPT_ENGINEERING.md](docs/PROMPT_ENGINEERING.md).

3. **Three-Layer Security Guards** (`malaika/guards/`): Every perception call passes through all three guards in sequence:
   - `input_guard.py` — file validation, size limits, format by magic bytes (not extension)
   - `content_filter.py` — prompt injection defense, PII scrubbing before model sees input
   - `output_validator.py` — JSON schema validation, confidence gating, physiological range checks
   See [docs/SECURITY.md](docs/SECURITY.md).

3. **Self-Correcting Inference**: When model output fails to parse, retry with a correction prompt (max 2 retries). If still unparseable, return `Uncertain` with raw output logged. Never crash, never guess. See `inference.py` retry pattern.

4. **Golden Dataset Evaluation**: 20+ clinical scenarios with known-correct WHO IMCI classifications. Run offline eval before every milestone. See `malaika/evaluation/`.

5. **Per-Step Observability** (`malaika/observability/`): Every IMCI step produces a trace:
   - `tracer.py` — input hash, prompt version, raw output, parsed result, confidence
   - `cost_tracker.py` — token count, inference latency, cumulative cost per assessment
   - `feedback.py` — links corrections to traces for prompt iteration

6. **Response Caching**: Hash-based cache for identical inference calls within a session. Same image analyzed twice? Serve from cache. Invalidated on model reload or prompt version change.

---

## Coding Standards (Summary — Full details in docs/DEVELOPMENT.md)

- **Python 3.11+** with strict type hints on all public APIs
- **Ruff** for linting and formatting (Google style, 100 char line length)
- **mypy --strict** must pass
- **pytest** for all tests, **pytest-cov** for coverage
- Every module has a corresponding test file
- Dataclasses over dicts for structured data
- Enums for states, classifications, severity levels
- No bare `except:` — always catch specific exceptions
- Logging via `structlog`, never `print()`
- Constants in UPPER_SNAKE_CASE in `config.py` or `imci_protocol.py`

---

## What Gemma 4 Does vs. What Code Does

This boundary is sacred. Never blur it.

### On Phone (Flutter — the primary demo)

| Gemma 4 E2B on Device | Deterministic Code (Dart) |
|------------------------|--------------------------|
| Rephrase IMCI questions naturally for caregivers | Manage Q&A state machine (`imci_questionnaire.dart`) |
| Analyze photo for alertness (eyes open? body limp?) | Parse vision response → boolean findings |
| Analyze photo for dehydration (sunken eyes? dry lips?) | Compare Q&A vs vision findings (`reconciliation_engine.dart`) |
| Analyze photo for wasting/edema (ribs visible? swollen feet?) | Apply WHO IMCI thresholds (`imci_protocol.dart`) |
| Generate caring summary report | Select treatment template based on classification |

**What the phone app does NOT do** (Python/Colab only):
- Voice conversation (STT/TTS) — phone is text-only
- Breathing rate from video — phone uses single photo from gallery
- Chest indrawing detection — requires observing breathing motion
- Audio/breath sound classification — no microphone input in Flutter
- Real-time continuous monitoring — single photo assessment
- 12-skill agentic architecture — phone uses simplified Q&A + vision

### On GPU/Colab (Python — supplementary demo)

| Gemma 4 E4B on GPU | Deterministic Code (Python) |
|---------------------|----------------------------|
| Understand speech in any language (`parse_caregiver_response`) | Parse findings into `_fields_answered` set |
| Analyze images for alertness (`assess_alertness`) | Compare against WHO danger sign criteria (p.2) |
| Classify breath sounds (`classify_breath_sounds`) | Route IMCI state machine transitions |
| Assess dehydration from photo (`assess_dehydration_signs`) | Count dehydration signs → severity level |
| Generate treatment instructions (`generate_treatment`) | Select treatment template based on classification |
| Emit structured events for UI | Render skill cards, classification cards, progress bar |

---

## Sprint Timeline (36 days — May 18 deadline)

| Phase | Dates | Focus | Status |
|-------|-------|-------|--------|
| 1: Foundation | Apr 12-18 | Gemma 4 running, data ready, basic pipeline | DONE |
| 2: Core IMCI | Apr 19-25 | Full assessment with vision + audio | IN PROGRESS |
| 3: Multilingual + Polish | Apr 26-May 2 | Languages, stability, stress testing | |
| 4: Fine-tuning + Deploy | May 3-9 | LoRA adapters, live URL, phone demo | |
| 5: Video + Submit | May 10-18 | Video production, writeup, submission | |

**Phase 1 Completed**: 104+ tests passing, 21/21 golden scenarios, skills-based agent architecture, voice pipeline with sentence-level TTS, Colab deployment via ngrok, fine-tuning v1-v5 (spectrogram approach).

**Phase 2 In Progress (Apr 19)**: Full IMCI Q&A + gallery photo vision analysis working end-to-end on Samsung A53. Reconciliation engine cross-references Q&A vs vision. All GPU crash issues resolved (fresh sessions, gallery picker). Text-only on phone (voice is Colab-only).

---

## Related Planning Documents

| Document | Purpose |
|----------|---------|
| [MASTERPLAN.md](MASTERPLAN.md) | Full execution plan with sprint details |
| [MALAIKA_PROPOSAL.md](MALAIKA_PROPOSAL.md) | Idea proposal, video script, why-it-wins |
| [RESEARCH.md](RESEARCH.md) | Competition analysis and research data |
| [DECISION_JOURNEY.md](DECISION_JOURNEY.md) | How we arrived at this idea |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Detailed implementation steps |
