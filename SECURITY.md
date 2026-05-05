# Security Policy

Malaika is a clinical-decision-support tool for child survival. A security flaw here is not just a CVE — it can mean a missed diagnosis on a sick child. We take reports seriously and will respond fast.

This document is the **vulnerability disclosure policy**. For the technical security architecture (input guards, content filters, output validators, prompt-injection defence, PII handling), see [`docs/SECURITY.md`](docs/SECURITY.md).

---

## Supported versions

Malaika is in pre-release development for the Gemma 4 Good Hackathon (deadline 2026-05-18). The `main` branch is the only supported version. Once a `v1.0` is tagged, this section will be updated.

| Version | Supported          |
| ------- | ------------------ |
| `main`  | :white_check_mark: |
| Hackathon submission tag | :white_check_mark: (best-effort during competition window) |
| Anything else | :x: |

---

## Reporting a vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Email the maintainers privately at the address listed in [`CITATION.cff`](CITATION.cff). If GitHub Private Vulnerability Reporting is enabled on this repository, you may also use that.

When reporting, please include:

1. **A description of the vulnerability** and its impact.
2. **Reproduction steps** — exact commands, inputs, model version, prompt version, code path.
3. **Affected component(s)** — Python package, Flutter app, web portal, notebook, fine-tuned adapter, configuration, dependency.
4. **Whether you have shared the vulnerability with anyone else.**
5. **Whether you wish to be credited** in the disclosure (default: yes, by handle of your choice).

We will acknowledge receipt within **72 hours** and aim to provide a substantive response within **7 days**. For active hackathon submission windows, we aim to respond within 48 hours.

---

## What we consider a security issue

Roughly, anything that could compromise the safety of a child being assessed, the privacy of their caregiver, or the integrity of a clinic's deployment.

Concretely:

### Clinical-safety issues (highest priority)

- A bypass of WHO IMCI thresholds in `malaika/imci_protocol.py` or `malaika_flutter/lib/core/imci_protocol.dart` — anything that causes a `SEVERE` classification to be reported as `MILD` or vice versa.
- A way to make Gemma 4's output influence the deterministic classifier — the boundary in [`CLAUDE.md`](CLAUDE.md) ("What Gemma 4 Does vs. What Code Does") must hold.
- Prompt-injection that causes the assistant to recommend a non-WHO-IMCI treatment, or to skip the danger-signs check.
- Output that bypasses the three-layer guard pipeline (`malaika/guards/`).

### Privacy issues

- Any path by which a photo, audio sample, transcript, or device identifier leaves the device unintentionally.
- Logging that captures PHI (patient health information) — names, ages, locations, faces, voices, photos — into telemetry, traces, error reports, or log files.
- Any storage of inference inputs/outputs beyond the documented retention window.

### Application-security issues (standard)

- OWASP Top 10 in the FastAPI server (`malaika/voice_app.py`), the Next.js portal (`web/`), or the Flutter app.
- Dependency vulnerabilities with proven exploit paths in our usage.
- Insecure model loading (loading untrusted model weights, deserialisation of untrusted pickles).
- Authentication bypass on the clinical portal or any future authenticated surface.

### Out of scope

- Vulnerabilities in Gemma 4 itself — please report those upstream to Google DeepMind.
- Vulnerabilities in third-party dependencies that do not affect Malaika's actual usage of them.
- Hypothetical risks without a reproducible attack.
- "The model gave a wrong answer" — report those as bugs, not security issues, unless the wrong answer is reachable through deliberate adversarial manipulation that bypasses our guards.

---

## Disclosure timeline

We follow coordinated disclosure:

1. Day 0: Report received, acknowledged within 72 hours.
2. Day 1–7: Triage, reproduce, assess severity (CVSS 3.1).
3. Day 7–30: Develop and test a fix. For clinical-safety issues, the fix is regression-tested against the 21 golden IMCI scenarios.
4. Day 30 (or earlier for low-risk fixes): Publish fix, credit the reporter in the release notes (unless they prefer otherwise).
5. Day 30–90 (depending on severity): Public advisory.

For actively exploited vulnerabilities, we will move faster and publish guidance even before a full fix is ready.

---

## Hardening notes for deployers

If you are running Malaika in a clinic or research deployment:

- **Pin the model version.** Both `Gemma 4 E2B` and `Gemma 4 E4B` weights should come from a known checksum. Never auto-update from an unverified source.
- **Pin the prompt version.** Prompt templates in `malaika/prompts/` carry a `VERSION` field — log it on every inference for reproducibility.
- **Run with the guards enabled.** All three: input, content, output. They are not optional.
- **Treat photo and audio as PHI.** Local storage only; encrypt at rest; redact in logs.
- **Do not connect the assessment device to the open internet** unless your deployment requires it. Malaika is designed to run offline.
- **Keep an audit log of classifications,** linked to prompt version and model checksum, for clinical incident review.

For the full architecture, see [`docs/SECURITY.md`](docs/SECURITY.md) and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Attribution

We credit reporters in the changelog and release notes unless they prefer to remain anonymous.

Thank you for helping keep Malaika safe.
