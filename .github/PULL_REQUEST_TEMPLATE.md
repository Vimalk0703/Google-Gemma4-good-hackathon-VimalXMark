# Pull Request

## What

<!-- One or two sentences. What does this change? -->

## Why

<!-- Why is this change needed? Link the issue if there is one. -->

Closes #

## How

<!-- High-level approach. Anything subtle a reviewer should know. -->

---

## Tier impact

- [ ] Tier 0 — phone (Flutter, Gemma 4 E2B)
- [ ] Tier 1 — clinic / server (Python, Gemma 4 E4B)
- [ ] Tier 2 — web portal (Next.js)
- [ ] Notebooks / training
- [ ] Docs / governance only

## Clinical-safety checklist

If this PR touches anything in `malaika/imci_protocol.py`, `malaika_flutter/lib/core/imci_protocol.dart`, `malaika/prompts/`, `malaika/guards/`, or `malaika/skills.py`, all of these must be checked:

- [ ] WHO IMCI thresholds remain in deterministic code, never in LLM output
- [ ] Three-layer guards (input → content → output) still run on every model call
- [ ] Prompt changes carry a bumped `VERSION` field
- [ ] The 21 golden IMCI scenarios still pass (`python -m malaika.evaluation.evaluator`)
- [ ] A second reviewer with WHO IMCI familiarity has been requested

If this PR does not touch clinical logic, write **N/A**.

## Verification

Mark every box that applies. Empty boxes are red flags.

- [ ] `make lint` passes (Python — ruff + mypy strict)
- [ ] `make test` passes (Python — pytest)
- [ ] `make coverage` ≥ 80% (Python)
- [ ] `flutter analyze` clean (Flutter)
- [ ] `flutter test` passes (Flutter)
- [ ] `npm run lint` clean (web)
- [ ] `npm run build` succeeds (web)
- [ ] Phone build tested on a real device — model + device + OS noted below
- [ ] Web changes manually verified in a browser
- [ ] Docs updated (README capability matrix, AGENTS.md, relevant `docs/*.md`)

### Manual test notes

<!-- Device / OS / browser / steps. "Tested on Samsung A53, Android 14, debug APK" — that level of detail. -->

## Risk and rollback

- **Blast radius**: <!-- which features could regress? -->
- **Rollback plan**: <!-- if this breaks in prod, how do we revert? -->

## Screenshots / recordings

<!-- For UI changes. Drag-and-drop into the PR. -->

---

By submitting this PR I confirm that I have read [`CONTRIBUTING.md`](../CONTRIBUTING.md) and [`AGENTS.md`](../AGENTS.md), and that this contribution is licensed under [Apache 2.0](../LICENSE).
