# Contributing to Malaika

Thank you for considering a contribution. Malaika is a WHO IMCI child-health assistant powered by Google Gemma 4 — every line of it must be safe enough to run in a real clinic, on a real phone, in a real village.

This document is the contract between contributors and the project. Read it before opening a PR.

---

## Table of contents

- [Code of Conduct](#code-of-conduct)
- [Before you contribute](#before-you-contribute)
- [Ground rules](#ground-rules)
- [Development setup](#development-setup)
- [Project layout](#project-layout)
- [Coding standards](#coding-standards)
- [Commit messages](#commit-messages)
- [Pull request process](#pull-request-process)
- [Reporting bugs](#reporting-bugs)
- [Reporting security issues](#reporting-security-issues)
- [License of contributions](#license-of-contributions)

---

## Code of Conduct

This project adheres to the [Contributor Covenant](CODE_OF_CONDUCT.md). By participating, you agree to uphold its terms. Report unacceptable behaviour to the maintainers (see `CITATION.cff` for contact).

---

## Before you contribute

Malaika is a clinical-decision-support tool. The bar for contributions is unusually high.

- **Read `CLAUDE.md`** — it is the law of this repo. The "Absolute Rules" section is non-negotiable.
- **Read `AGENTS.md`** if you are an AI agent or are using one to contribute.
- **Read `docs/ENGINEERING_PRINCIPLES.md`** before writing code.
- **Read `docs/SECURITY.md`** before touching anything that handles user input or model output.
- **Read `docs/TESTING_STRATEGY.md`** before writing tests.

If you are proposing a substantial change (a new clinical skill, a new modality, a model swap), open a GitHub issue first and reach agreement with maintainers before writing the code.

---

## Ground rules

These are derived from the project's hard-won principles. Breaking any of them is grounds for a PR being closed.

1. **Mobile first.** The Flutter app on a $60 Android is the primary surface. If a feature only works on a GPU, it does not ship to the phone tier.
2. **Offline by default.** Every Tier 0 feature must work without internet. No exceptions.
3. **All intelligence comes from Gemma 4.** No other LLMs. Gemma 4 is the project's reason to exist, not a tool we happen to use.
4. **Medical safety first.** WHO IMCI thresholds are deterministic code, never LLM output. Read `malaika/imci_protocol.py` and `malaika_flutter/lib/core/imci_protocol.dart` before touching classification logic.
5. **Three-layer guards on every model call.** `input_guard` → `content_filter` → `output_validator`. See `malaika/guards/`.
6. **Versioned prompts.** Every prompt to Gemma 4 lives in `malaika/prompts/` as a typed `PromptTemplate`. No hardcoded prompt strings in service code.
7. **Tests before merge.** Every new module gets a test file. Every clinical change runs against the 21 golden IMCI scenarios. Coverage threshold is 80%.
8. **No half-baked rewrites.** Don't replace working code with untested rewrites. Build the new thing alongside the old, switch when proven, then delete the old.
9. **No demo mode.** Real Gemma 4, real inference, real model. No mocks except in unit tests.

---

## Development setup

### Python (Tier 1 server, notebooks, evaluation)

```bash
# 3.11+ required
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pip install -r requirements-dev.txt
```

Run the test suite:

```bash
make test            # or: pytest tests/ -v
make lint            # ruff + mypy
make format          # ruff format
make coverage        # pytest --cov
```

### Flutter (Tier 0 phone app)

```bash
cd malaika_flutter
flutter pub get
flutter analyze                # lint
flutter test                   # unit tests
flutter build apk --debug      # debug APK
```

Requires Flutter `>=3.24.0`, Dart `>=3.5.0`, Android SDK 34+. Tested on Samsung A53 (Mali G68 GPU). See `malaika_flutter/README.md` for the GPU memory constraint.

### Web (clinical portal)

```bash
cd web
cp .env.example .env.local       # set BREATH_API_URL and PORTAL_PASSCODE
npm install
npm run dev                      # http://localhost:3000
npm run build && npm start       # production build
npm run lint                     # next lint
```

---

## Project layout

See [`AGENTS.md`](AGENTS.md) for the canonical machine-readable map of the repo. The high-level layout:

```
malaika/             Python package — Tier 1 server, agentic skills, evaluation
malaika_flutter/     Flutter Android app — Tier 0 offline phone tier
web/                 Next.js 16 landing + clinical portal
notebooks/           Colab/Kaggle notebooks (model training, server deployment)
docs/                Engineering documentation (architecture, security, testing, prompts)
tests/               Python test suite (104+ tests, 21 golden IMCI scenarios)
adapters/            Fine-tuned LoRA adapter weights (gitignored)
configs/             YAML/JSON configuration
scripts/             One-off scripts (data prep, benchmarks, exports)
```

---

## Coding standards

### Python

- **Python 3.11+** with strict type hints on every public API.
- **Ruff** for lint and format (`pyproject.toml` is the source of truth — Google style, 100-char line length, security rules enabled).
- **mypy --strict** must pass. No `Any` returns from public APIs.
- **No bare `except:`.** Catch the specific exception class.
- **Logging via `structlog`,** never `print()`.
- **Dataclasses** over dicts for structured data. **Enums** for states and classifications.
- **Constants** in `UPPER_SNAKE_CASE` in `config.py` or `imci_protocol.py`.
- Every module has a corresponding test file under `tests/` with the same path.

### Dart / Flutter

- **`flutter analyze` clean** — `analysis_options.yaml` is the source of truth.
- **Null-safety throughout.** No `late` without justification.
- **Immutable widgets where possible.** `const` constructors.
- **No business logic in widgets.** Logic lives in `lib/core/` or `lib/inference/`.

### TypeScript / Next.js

- **Strict TypeScript** (`"strict": true` in `tsconfig.json`).
- **`npm run lint` clean** before merge.
- **Server actions** for any non-trivial server-side mutation. No client-side secrets.

---

## Commit messages

Conventional Commits. See recent `git log` for the cadence the project uses.

```
feat(scope): short imperative
fix(scope): short imperative
docs(scope): short imperative
test(scope): short imperative
refactor(scope): short imperative
chore(scope): short imperative
```

Scopes used in this repo: `flutter`, `web`, `notebook`, `agent`, `protocol`, `prompts`, `guards`, `eval`, `docs`, `ci`.

The body, when present, explains *why*. The diff already explains *what*.

---

## Pull request process

1. **Open an issue first** for non-trivial changes. Link the issue from the PR.
2. **Branch from `main`** with a descriptive name: `feat/breath-classifier-eval`, `fix/imci-fever-edge-case`.
3. **Keep PRs small.** A reviewable PR is under ~400 lines of diff. Larger work gets split.
4. **Run all checks locally:**
   - Python: `make lint && make test`
   - Flutter: `flutter analyze && flutter test`
   - Web: `npm run lint`
5. **Add or update tests.** A clinical-logic change without a test does not merge.
6. **Update docs.** If you changed an API, update its doc. If you added a feature, update the README's capability matrix.
7. **Fill in the PR template** completely. The checklist exists for a reason.
8. **CI must be green** before review.
9. **Two-eyes rule for clinical logic.** Anything in `imci_protocol.py`, `imci_protocol.dart`, the prompt templates, or the guards needs a second reviewer who has read the WHO IMCI manual.

---

## Reporting bugs

Open a GitHub issue using the "Bug report" template. Include:

- Repro steps
- Expected vs observed behaviour
- Environment (OS, Python/Flutter/Node version, device for phone bugs)
- Logs (redact any PHI — see [SECURITY.md](SECURITY.md))

For ambiguous behaviour from Gemma 4 itself (parsing failures, weird outputs), include the prompt version (`malaika/prompts/<topic>.py` `VERSION`) and the raw model output.

---

## Reporting security issues

**Do not open a public issue for security vulnerabilities.** See [`SECURITY.md`](SECURITY.md) for the disclosure process.

---

## License of contributions

By contributing to Malaika you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE), the same license that covers the rest of the project. You retain copyright; you grant the project the rights described in the Apache 2.0 grant clauses.

---

> *Pneumonia kills a child every thirty-nine seconds. Code accordingly.*
