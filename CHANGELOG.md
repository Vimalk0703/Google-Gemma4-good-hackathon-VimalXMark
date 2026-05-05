# Changelog

All notable changes to **Malaika** are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Dates are in `YYYY-MM-DD` (UTC).

---

## [Unreleased]

### Added
- Repository governance package: `LICENSE` (Apache 2.0), `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1), `SECURITY.md` (vulnerability disclosure), `AGENTS.md` (canonical guide for AI coding/judging agents), `CITATION.cff`.
- `.github/` folder: pull-request template, bug-report and feature-request issue templates, Dependabot configuration covering Python / npm / pub / GitHub Actions, CI workflow running ruff + mypy + pytest + `flutter analyze` + `flutter test` + Next.js lint and build.
- Top-level `Makefile` exposing `make lint`, `make test`, `make coverage`, `make golden`, `make flutter-*`, `make web-*`, `make ci`.
- `.editorconfig` for consistent indentation and line endings across editors.
- `CHANGELOG.md` (this file).
- `docs/README.md` index of the engineering documentation set.
- Tightened `malaika_flutter/analysis_options.yaml` with correctness-first lint rules.
- Replaced the boilerplate `malaika_flutter/README.md` with a real architecture / build / capability-matrix document.

### Fixed
- `pyproject.toml` build-backend was set to `setuptools.backends._legacy:_Backend`, an invalid path that broke `pip install -e .`. Corrected to `setuptools.build_meta`.

### Changed
- Reorganised root markdown: archived development artefacts (`MASTERPLAN.md`, `RESEARCH.md`, `DECISION_JOURNEY.md`, `IMPLEMENTATION_PLAN.md`, `MALAIKA_PROPOSAL.md`, `ENHANCEMENT_PLAN.md`, `TRACKER.md`, draft video scripts) into `docs/history/` to keep the repository entry surface focused on the README and governance files.
- Added badges (license, Python, Flutter) and an updated structure section to `README.md`.

---

## [0.1.0] — 2026-04-19

### Added
- Initial Tier 1 Python package (`malaika/`): inference wrapper, agentic chat engine, 12-skill registry with `BeliefState`, FastAPI voice server, real-time voice pipeline, Gradio fallback UI.
- WHO IMCI deterministic engine (`imci_protocol.py`, `imci_engine.py`) with 78 threshold tests and 21 golden clinical scenarios passing.
- Versioned prompt templates in `malaika/prompts/` covering danger signs, breathing, diarrhoea, fever, nutrition, heart, treatment, speech, system persona.
- Three-layer guard pipeline (`malaika/guards/`): input validation by magic byte, content filter for prompt injection and PII, output validator for JSON schema and confidence gating.
- Per-step observability stack (`malaika/observability/`): tracer, cost tracker, feedback link.
- Tier 0 Flutter Android app (`malaika_flutter/`) running Gemma 4 E2B locally via `flutter_gemma`. End-to-end IMCI Q&A + gallery photo vision analysis + Q&A vs vision reconciliation + deterministic classification on Samsung A53 (Mali G68 GPU).
- Offline voice loop (STT + TTS) via Android native engines on the phone tier.
- Tier 2 Next.js 16 clinical portal landing page + browser audio recording.
- Notebooks for Colab demonstration and fine-tuning (PEFT v1–v5, Unsloth-native).
- Engineering documentation set: `docs/ARCHITECTURE.md`, `docs/ENGINEERING_PRINCIPLES.md`, `docs/TESTING_STRATEGY.md`, `docs/SECURITY.md`, `docs/DEVELOPMENT.md`, `docs/PROMPT_ENGINEERING.md`.

[Unreleased]: https://github.com/klickgenai/deepmind-hackathon/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/klickgenai/deepmind-hackathon/releases/tag/v0.1.0
