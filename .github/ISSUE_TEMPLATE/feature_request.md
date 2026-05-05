---
name: Feature request
about: Propose a new clinical capability, technical improvement, or quality-of-life change
title: "[feat] "
labels: enhancement, triage
assignees: ''
---

> Before filing: read [`CLAUDE.md`](../../CLAUDE.md) "Absolute Rules" and [`AGENTS.md`](../../AGENTS.md). Many feature ideas are excluded by the project's intentional scope (no second LLM, no online dependencies, no GPU-only features on Tier 0). Save us both time by checking these first.

## Problem

<!-- What problem does this solve? Whose problem? Be specific — "community health workers" is not a user; "an HEW in a rural clinic with intermittent power" is. -->

## Proposed solution

<!-- High-level approach. Don't write the code yet. -->

## Tier

- [ ] Tier 0 — phone (Flutter, must work offline on Mali G68 GPU)
- [ ] Tier 1 — clinic / server (Python, GPU available)
- [ ] Tier 2 — web portal
- [ ] Notebooks / training

## Clinical justification

If this adds a clinical capability, cite the WHO IMCI page or evidence supporting it. Don't invent clinical content.

## Why this and not just more of the existing thing

The maintainer's policy: **one killer use case, not five shallow ones.** Make the case that this deepens the IMCI assessment rather than adding feature breadth.

## Out-of-scope check

- [ ] Does not require a second LLM (only Gemma 4)
- [ ] Does not require online connectivity for Tier 0
- [ ] Does not require capabilities the phone GPU can't support (camera + LLM simultaneously, video processing, large multimodal context)
- [ ] Does not blur the LLM-vs-deterministic-code boundary

## Alternatives considered

<!-- What did you reject and why? -->

## Acceptance criteria

How will we know this is done?

- [ ] ...
- [ ] Tests added (unit + at least one golden scenario if clinical)
- [ ] Docs updated
