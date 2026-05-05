# AGENTS.md

> A canonical, machine-readable guide for AI coding agents and reviewing agents working on Malaika.
> Humans should read [`CONTRIBUTING.md`](CONTRIBUTING.md) instead.

If you are an AI agent (Claude Code, Cursor, Codex, GitHub Copilot Chat, an autonomous coding agent, or a judging agent for the Gemma 4 Good Hackathon) — this file is your starting point. Read it fully before reading any other file.

---

## What this project is

Malaika ("Angel" in Swahili) is a fully-offline, on-device implementation of the World Health Organization's [Integrated Management of Childhood Illness (IMCI)](https://www.who.int/publications/i/item/9789241506823) protocol, powered by Google's **Gemma 4** open-weights model.

- **Tier 0 — phone**: Flutter Android app, Gemma 4 E2B (~2.6 GB), runs on a $60 phone with no internet.
- **Tier 1 — village clinic**: Gemma 4 E4B with fine-tuned LoRA adapters, plus a breath-sound classifier, on a single GPU.
- **Tier 2 — clinical portal**: Next.js 16 web portal for community health workers reviewing cases.

Submission: **Google Gemma 4 Good Hackathon**, deadline **2026-05-18**, prize target $70K (Main + Health + Unsloth).

---

## Read these in this order

| # | File | Why |
|---|------|-----|
| 1 | [`CLAUDE.md`](CLAUDE.md) | The project's law. Absolute Rules in particular are non-negotiable. |
| 2 | [`README.md`](README.md) | The pitch, the architecture, the capabilities. |
| 3 | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System architecture, data flow, deployment topology. |
| 4 | [`docs/ENGINEERING_PRINCIPLES.md`](docs/ENGINEERING_PRINCIPLES.md) | Design principles and error-handling philosophy. |
| 5 | [`docs/SECURITY.md`](docs/SECURITY.md) | The three-layer guard pipeline. Mandatory before touching anything model-facing. |
| 6 | [`docs/PROMPT_ENGINEERING.md`](docs/PROMPT_ENGINEERING.md) | How prompts are versioned and tested. |
| 7 | [`docs/TESTING_STRATEGY.md`](docs/TESTING_STRATEGY.md) | How to test clinical-safety code. |
| 8 | [`malaika/imci_protocol.py`](malaika/imci_protocol.py) | The deterministic WHO IMCI thresholds — these are clinical truth, not LLM output. |
| 9 | [`malaika_flutter/lib/core/imci_protocol.dart`](malaika_flutter/lib/core/imci_protocol.dart) | The Dart equivalent of the above. Must stay in lockstep. |

---

## Hard rules — failing any of these will get your PR closed

These are derived from [`CLAUDE.md`](CLAUDE.md) and from corrections the maintainer has logged in his agent memory. Treat them as binding.

1. **Mobile first.** The Flutter app is the primary surface. If a feature only works on a GPU, it does not ship to the phone tier. Do not propose video-breath-counting or chest-indrawing detection on the phone.
2. **Offline by default.** Tier 0 features must work without internet. No telemetry, no remote inference, no analytics on Tier 0.
3. **All intelligence comes from Gemma 4.** No other LLMs. Not for fallback, not for "easy parts," not even in tests.
4. **Medical safety first.** Classifications come from deterministic code in `imci_protocol.py` / `imci_protocol.dart`, never from LLM output. The boundary in `CLAUDE.md` ("What Gemma 4 Does vs. What Code Does") is sacred.
5. **No demo mode.** No mock LLMs. No fake-it-till-you-make-it. Real Gemma 4, every time, except in pure unit tests.
6. **No half-baked rewrites.** Do not replace working code with untested rewrites. Build the new thing alongside the old, switch when proven, then delete the old.
7. **One killer use case.** This is not a feature shop. Don't add 5 shallow features; deepen the IMCI assessment instead.
8. **Three-layer guards.** Every model call goes through `input_guard` → `content_filter` → `output_validator`. No exceptions.
9. **Versioned prompts.** Every prompt to Gemma 4 lives in `malaika/prompts/<topic>.py` as a typed `PromptTemplate`. No hardcoded prompt strings in service code.
10. **Tests before merge.** Every new module gets a test file. Coverage threshold is 80%. Clinical changes are regression-tested against the 21 golden IMCI scenarios in `malaika/evaluation/`.

---

## File map

```
deepmind-hackathon/
├── README.md                           # Pitch + capability matrix
├── CLAUDE.md                           # Project law, absolute rules
├── AGENTS.md                           # ← you are here
├── CONTRIBUTING.md                     # For human contributors
├── CODE_OF_CONDUCT.md                  # Contributor Covenant 2.1
├── SECURITY.md                         # Vulnerability disclosure (root)
├── LICENSE                             # Apache 2.0
├── CITATION.cff                        # Citation metadata
├── CHANGELOG.md                        # Keep a Changelog format
├── Makefile                            # make test | lint | format | coverage | build
├── pyproject.toml                      # Python build, ruff, mypy, pytest, coverage
├── requirements*.txt                   # Pinned Python deps
│
├── malaika/                            # PYTHON PACKAGE — Tier 1 server, agentic skills, eval
│   ├── inference.py                    # MalaikaInference — single Gemma 4 wrapper, all modalities
│   ├── chat_engine.py                  # Agentic IMCI conversation orchestrator
│   ├── skills.py                       # SkillRegistry — 12 clinical skills + BeliefState
│   ├── voice_app.py                    # FastAPI server (REST + WebSocket voice)
│   ├── voice_session.py                # Real-time voice pipeline
│   ├── imci_engine.py                  # IMCI state machine (Gradio path)
│   ├── imci_protocol.py                # WHO threshold constants — CLINICAL TRUTH, deterministic
│   ├── vision.py                       # Image/video analysis via Gemma 4
│   ├── audio.py                        # Audio analysis via Gemma 4
│   ├── tts.py                          # Piper TTS (offline)
│   ├── app.py                          # Gradio UI entry point
│   ├── config.py                       # Feature flags, model paths, thresholds
│   ├── types.py                        # Shared dataclasses, enums
│   ├── utils.py                        # Shared utilities
│   ├── prompts/                        # PromptTemplate objects — NEVER hardcode prompts
│   │   ├── base.py                     # PromptTemplate base class + VERSION field
│   │   ├── danger_signs.py
│   │   ├── breathing.py
│   │   ├── diarrhea.py
│   │   ├── fever.py
│   │   ├── nutrition.py
│   │   ├── heart.py
│   │   ├── treatment.py
│   │   ├── speech.py
│   │   └── system.py                   # Malaika persona
│   ├── guards/                         # THREE-LAYER SECURITY — required for every model call
│   │   ├── input_guard.py              # Magic-byte file validation, size limits
│   │   ├── content_filter.py           # Prompt-injection defence, PII scrubbing
│   │   └── output_validator.py         # JSON schema, confidence gating, range checks
│   ├── observability/                  # Per-IMCI-step traces, costs, feedback
│   │   ├── tracer.py
│   │   ├── cost_tracker.py
│   │   └── feedback.py
│   ├── evaluation/                     # 21 golden IMCI scenarios + offline evaluator
│   │   ├── golden_scenarios.py
│   │   └── evaluator.py
│   └── static/                         # Voice UI assets (orb, skill cards)
│
├── malaika_flutter/                    # PRIMARY DEMO — Android app with Gemma 4 E2B
│   ├── lib/
│   │   ├── screens/
│   │   │   ├── splash_screen.dart      # Model download + GPU init
│   │   │   ├── dashboard_screen.dart   # Main menu
│   │   │   ├── home_screen.dart        # IMCI Q&A orchestrator (~970 lines)
│   │   │   └── camera_monitor_screen.dart # Gallery photo picker + vision analysis
│   │   ├── core/
│   │   │   ├── imci_questionnaire.dart # Structured IMCI questions + answer parsing
│   │   │   ├── imci_protocol.dart      # WHO thresholds — must match Python
│   │   │   ├── imci_types.dart         # Severity / classification enums
│   │   │   ├── reconciliation_engine.dart # Q&A vs vision cross-reference
│   │   │   └── voice_service.dart      # Offline STT + TTS via Android native
│   │   ├── theme/malaika_theme.dart
│   │   ├── widgets/
│   │   │   ├── chat_bubble.dart
│   │   │   ├── imci_progress_bar.dart
│   │   │   ├── classification_card.dart
│   │   │   └── reasoning_card.dart
│   │   └── inference/model_manager.dart
│   ├── analysis_options.yaml           # Dart linter config
│   └── pubspec.yaml
│
├── web/                                # Next.js 16 clinical portal + landing
│   ├── app/                            # App Router
│   ├── components/
│   ├── package.json
│   └── README.md
│
├── notebooks/                          # Colab / Kaggle
│   ├── 10_voice_agent_colab.ipynb      # Voice agent on T4 (supplementary demo)
│   ├── 09_chat_app_colab.ipynb
│   ├── 08_colab_run_app.ipynb
│   └── (fine-tuning notebooks)
│
├── tests/                              # Mirrors malaika/ structure (104+ tests passing)
│   ├── test_imci_protocol.py           # 78 WHO threshold tests
│   ├── test_imci_engine.py             # 26 state-machine tests
│   ├── test_inference.py
│   ├── test_vision.py
│   ├── test_audio.py
│   ├── test_prompts.py
│   ├── test_guards.py
│   └── conftest.py
│
├── docs/                               # Engineering documentation
│   ├── README.md                       # Index
│   ├── ARCHITECTURE.md
│   ├── ENGINEERING_PRINCIPLES.md
│   ├── TESTING_STRATEGY.md
│   ├── SECURITY.md                     # Technical guard architecture
│   ├── DEVELOPMENT.md
│   ├── PROMPT_ENGINEERING.md
│   ├── SESSION_LOG.md                  # Detailed dev journal
│   └── history/                        # Archived planning docs
│
├── adapters/                           # Fine-tuned LoRA adapters (gitignored)
├── configs/                            # YAML/JSON config (features.yaml, etc.)
├── data/                               # Datasets (gitignored)
└── scripts/                            # One-off scripts (data prep, benchmarks, exports)
```

---

## Where to start, by intent

| If you want to… | Start at | Then read |
|------|----------|-----------|
| Understand the pitch | `README.md` | `MALAIKA_PROPOSAL.md` (if present in `docs/history/`) |
| Add a clinical skill | `malaika/skills.py` | `docs/ARCHITECTURE.md` "Skills" section, then any existing skill (e.g., `breathing.py` prompt + corresponding skill registration) |
| Touch IMCI classification | `malaika/imci_protocol.py` AND `malaika_flutter/lib/core/imci_protocol.dart` | `docs/TESTING_STRATEGY.md`, then run `pytest tests/test_imci_protocol.py -v` and the 21 golden scenarios |
| Add or modify a prompt | `malaika/prompts/<topic>.py` | `docs/PROMPT_ENGINEERING.md` — bump `VERSION` and update tests |
| Touch model I/O | `malaika/inference.py` | `docs/SECURITY.md` (guards are mandatory) |
| Phone-app feature | `malaika_flutter/lib/screens/home_screen.dart` | `CLAUDE.md` "Phone App — What ACTUALLY Works" — do NOT exceed that capability matrix |
| Web portal feature | `web/app/` | `web/README.md` |
| Fine-tuning | `notebooks/` (Unsloth-native) | `project_finetuning_status` memory and any Unsloth notebook |

---

## How to verify any claim made in this repo

Hackathon claims are easy to inflate. The maintainer is allergic to it. Use these to keep yourself honest:

| Claim type | How to verify |
|------|---------------|
| "X test passes" | `pytest tests/test_X.py -v` |
| "Coverage ≥ 80%" | `make coverage` (fails if under) |
| "Lint clean" | `make lint` (ruff) and `cd malaika_flutter && flutter analyze` |
| "WHO threshold correct" | Cross-reference `malaika/imci_protocol.py` constants against the WHO IMCI chart booklet PDF — every constant should have a comment citing the page |
| "Phone feature works" | Build the APK and run on Samsung A53 (Mali G68). Do not claim feature works without a successful on-device test — see "Phone App — What ACTUALLY Works" in `CLAUDE.md` |
| "Prompt produces X" | The prompt file's tests in `tests/test_prompts.py` should assert it. If they don't, add the test before claiming the behaviour. |
| "Golden scenario passes" | `python -m malaika.evaluation.evaluator` |

If you cannot verify a claim with one of the above, **do not assert it.**

---

## What Gemma 4 does vs. what code does

This boundary is sacred. The LLM does perception and language. The code makes the medical decision.

**Gemma 4's job:**
- Rephrase IMCI questions naturally for caregivers
- Understand caregiver responses in any language
- Analyse photos for alertness, dehydration signs, wasting, oedema
- Classify breath sounds (Tier 1 only)
- Generate a caring, language-appropriate summary

**Code's job:**
- Manage the IMCI state machine
- Parse Gemma 4's perception output into typed findings
- Apply WHO IMCI thresholds (constants in `imci_protocol.py`)
- Decide the classification (`SEVERE` / `MODERATE` / `MILD`)
- Select the treatment template based on classification
- Run the three-layer guards on every model call

**What Gemma 4 does NOT do:**
- It does not output classifications.
- It does not output threshold values.
- It does not pick treatments.
- Its output is never trusted without passing through `output_validator.py`.

If a contribution blurs this line, reject it.

---

## Phone-app capability matrix (do not exceed)

The Tier 0 Flutter app on Samsung A53 (Mali G68 GPU, 2.5 GB usable) supports exactly this:

| Feature | Status |
|---|---|
| Text-based IMCI Q&A | works |
| Photo-from-gallery → vision analysis | works |
| Q&A vs vision reconciliation | works |
| WHO IMCI classification (deterministic) | works |
| Final report with severity + treatment | works |
| Voice input/output (offline STT+TTS via Android native CPU engines) | works |
| Fully offline | works |
| In-app camera preview | **does not work** — Mali GPU has no headroom |
| System-camera capture | **does not work** — Android OOM-kills the app on background |
| Breathing-rate from video | **does not work** — no video processing on phone |
| Chest-indrawing detection | **does not work** — needs motion observation |
| Audio/breath-sound classification | **does not work** — Tier 1 only, runs on the clinic GPU |
| Real-time continuous monitoring | **does not work** — single-photo assessment only |

If your contribution requires any "does not work" item, it belongs in Tier 1 (Python / GPU / `notebooks/`), not the phone.

---

## Common pitfalls (mistakes prior agents have made)

These are the classes of mistake the maintainer has had to correct. Avoid them.

- **Inventing a capability that "should be easy."** It is not. Every Tier 0 feature was selected because it survives the GPU memory constraint.
- **Using a non-Gemma model "just for one part."** The competition rules and the project rules forbid it. There is exactly one model.
- **Hardcoding a prompt inline.** All prompts go through `PromptTemplate` in `malaika/prompts/`.
- **Skipping a guard.** "It's just a quick test path" is not an excuse — guards are unconditional.
- **Mocking the model in integration tests.** Unit tests can mock; integration tests must run real inference (GPU available in `notebooks/`).
- **Adding fields to `BeliefState` without an `ENUM` for the source.** Every finding has a typed origin (`Q_AND_A`, `VISION`, `AUDIO`, `RECONCILED`).
- **Treating deterministic classification as if it were a model job.** It is not. The classifier is a function over thresholds; if you find yourself asking the model "what classification is this?", you are doing it wrong.
- **Big-bang rewrites.** Build alongside, prove, switch, delete. Never break a working path with an unproven one.

---

## Verification quick reference

```bash
# Python
make test                    # pytest tests/ -v
make lint                    # ruff + mypy --strict
make coverage                # pytest --cov, fails under 80%
make format                  # ruff format

# Flutter
cd malaika_flutter
flutter analyze              # lint
flutter test                 # unit tests
flutter build apk --debug    # debug APK

# Web
cd web
npm run lint                 # next lint
npm run build                # production build smoke test

# Golden IMCI scenarios
python -m malaika.evaluation.evaluator
```

If `main` doesn't pass these, that's a bug to file before you start your own work.

---

## Final word

This project is judged not just on output but on craft. Every commit, every PR, every line of code should answer the question: *would a reviewer who has read the WHO IMCI manual, who has built clinical software before, and who has audited a thousand AI agents — would they trust this code on a sick child?*

If the answer is "not quite yet," do another pass.
