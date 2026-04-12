# Malaika — Project Instructions

> **Malaika** (Angel in Swahili): WHO IMCI child survival AI powered by Gemma 4, running fully offline on any phone.
> **Competition**: Google Gemma 4 Good Hackathon | **Deadline**: May 18, 2026 | **Prize target**: $70K (Main + Health + Unsloth)

---

## Absolute Rules

1. **EVERYTHING runs offline. No internet. No exceptions.** Every feature must work without connectivity.
2. **ALL intelligence comes from Gemma 4.** It IS the solution, not a tool we use. No other LLMs.
3. **Every claim must be implementable.** No hand-waving. If it's in the writeup, it works in the demo.
4. **Medical safety first.** This is decision SUPPORT, not diagnosis. WHO IMCI thresholds are deterministic code, never LLM output.
5. **Single developer model.** No assumptions about who does what — any task can be picked up by anyone.

---

## Project Structure

```
malaika/                  # Main Python package
  __init__.py
  inference.py            # MalaikaInference — single Gemma 4 model, all modalities
  imci_engine.py          # IMCI protocol state machine (deterministic)
  imci_protocol.py        # WHO threshold constants and classification logic
  vision.py               # Image/video analysis via Gemma 4
  audio.py                # Audio analysis (breath sounds, speech) via Gemma 4
  tts.py                  # Piper TTS output (offline text-to-speech)
  app.py                  # Gradio UI entry point
  config.py               # Feature flags, model paths, thresholds
  types.py                # Shared type definitions (dataclasses, enums)
  utils.py                # Shared utilities (logging, file handling)

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

tests/                    # All tests (mirrors malaika/ structure)
  test_inference.py
  test_imci_engine.py
  test_imci_protocol.py
  test_vision.py
  test_audio.py
  test_prompts.py         # Prompt rendering and parsing tests
  test_guards.py          # Input/content/output guard tests
  conftest.py             # Shared fixtures

scripts/                  # One-off scripts (data prep, benchmarks, exports)
adapters/                 # Fine-tuned LoRA adapter weights
configs/                  # YAML/JSON config files
data/                     # Datasets (gitignored, downloaded via scripts)
docs/                     # Engineering documentation (see below)
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

## Quick Reference

### Models
- **Gemma 4 E4B** (4.5B active): Demo machine via Transformers. Fine-tuned with LoRA. ~5-6GB VRAM in 4-bit.
- **Gemma 4 E2B** (2.3B active): Phone via LiteRT-LM. Base model. 50+ tok/s, 2.58GB disk. Video proof.

### IMCI Flow
```
START -> DANGER_SIGNS -> BREATHING -> DIARRHEA -> FEVER -> NUTRITION -> [HEART_MEMS] -> CLASSIFY -> TREAT
```

### Key Commands
```bash
# Run the app
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

### Feature Flags (configs/features.yaml)
```yaml
enable_heart_rate: false    # MEMS heart module — GO/NO-GO decision pending
enable_tts: true            # Piper TTS spoken output
enable_video_breathing: true # Breathing rate from video (vs frame-by-frame fallback)
enable_multilingual: true   # Multi-language support
```

---

## Production AI Patterns (Inspired by 9-Layer Architecture)

These patterns elevate Malaika from hackathon code to production-grade AI:

1. **Prompts as Code**: All Gemma 4 prompts are versioned `PromptTemplate` objects in `malaika/prompts/`. Never hardcode prompt strings in service logic. See [docs/PROMPT_ENGINEERING.md](docs/PROMPT_ENGINEERING.md).

2. **Three-Layer Security Guards** (`malaika/guards/`): Every perception call passes through all three guards in sequence:
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

| Gemma 4 (AI Intelligence) | Deterministic Code (Logic) |
|---------------------------|---------------------------|
| Understand speech in any language | Parse Gemma's response into structured data |
| Analyze images (chest indrawing, skin color, wasting) | Compare values against WHO thresholds |
| Classify breath sounds (wheeze, stridor, grunting) | Route IMCI state machine transitions |
| Count breathing rate from video | Apply `if rate >= 50: classify("fast_breathing")` |
| Generate treatment instructions in local language | Select treatment template based on classification |

---

## Sprint Timeline (36 days — May 18 deadline)

| Phase | Dates | Focus |
|-------|-------|-------|
| 1: Foundation | Apr 12-18 | Gemma 4 running, data ready, basic pipeline |
| 2: Core IMCI | Apr 19-25 | Full assessment with vision + audio |
| 3: Multilingual + Polish | Apr 26-May 2 | Languages, stability, stress testing |
| 4: Fine-tuning + Deploy | May 3-9 | LoRA adapters, live URL, phone demo |
| 5: Video + Submit | May 10-18 | Video production, writeup, submission |

---

## Related Planning Documents

| Document | Purpose |
|----------|---------|
| [MASTERPLAN.md](MASTERPLAN.md) | Full execution plan with sprint details |
| [MALAIKA_PROPOSAL.md](MALAIKA_PROPOSAL.md) | Idea proposal, video script, why-it-wins |
| [RESEARCH.md](RESEARCH.md) | Competition analysis and research data |
| [DECISION_JOURNEY.md](DECISION_JOURNEY.md) | How we arrived at this idea |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Detailed implementation steps |
