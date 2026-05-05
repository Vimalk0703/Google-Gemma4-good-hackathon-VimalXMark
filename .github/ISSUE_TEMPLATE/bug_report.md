---
name: Bug report
about: Report unexpected behaviour
title: "[bug] "
labels: bug, triage
assignees: ''
---

## Summary

<!-- One sentence: what's wrong? -->

## Tier

- [ ] Tier 0 — phone (Flutter)
- [ ] Tier 1 — Python server / notebook
- [ ] Tier 2 — web portal
- [ ] Other (specify)

## Severity

- [ ] Clinical-safety risk (wrong classification, threshold bypass, prompt-injection)
- [ ] Privacy risk (PHI leakage, telemetry in offline mode)
- [ ] Crash / data loss
- [ ] Functional bug (feature does not work)
- [ ] UI / UX
- [ ] Performance

> If this is a security or clinical-safety vulnerability, **stop** and follow [`SECURITY.md`](../../SECURITY.md) instead — do not file a public issue.

## Reproduction

Exact steps. Copy-pasteable commands where possible.

```
1. ...
2. ...
3. ...
```

## Expected behaviour

## Actual behaviour

## Environment

- OS:
- Python version (if Tier 1):
- Flutter version (if Tier 0):
- Device + Android version (if Tier 0):
- Node version (if Tier 2):
- Model: <!-- Gemma 4 E2B / E4B / fine-tuned adapter version -->
- Prompt version (if applicable):

## Logs

Redact any PHI before pasting.

```
<paste logs here>
```

## Anything else

<!-- Screenshots, recordings, hypotheses. -->
