# Archived planning documents

This folder contains the planning, research, and ideation documents written during Malaika's design and early build phases. They are kept here for the historical record — to show the decision journey, the analysis behind choices, and the trade-offs considered. They are **not** the source of truth for day-to-day development.

For current information, prefer in this order:

1. The top-level [`README.md`](../../README.md) — what Malaika is and what it does.
2. The top-level [`CLAUDE.md`](../../CLAUDE.md) — project law, absolute rules, what works on the phone today.
3. The top-level [`AGENTS.md`](../../AGENTS.md) — canonical guide for AI coding/judging agents.
4. The engineering docs at [`../`](../) — architecture, security, testing, prompt engineering.

---

## Index

| File | Phase | Purpose |
|------|-------|---------|
| [`MASTERPLAN.md`](MASTERPLAN.md) | Pre-build | Full execution plan with sprint details. The closest thing to a living plan-of-record this project still has. |
| [`MALAIKA_PROPOSAL.md`](MALAIKA_PROPOSAL.md) | Pre-build | The original idea proposal, video script, and "why this wins" argument. |
| [`RESEARCH.md`](RESEARCH.md) | Pre-build | Competition landscape, prior winner analysis, opportunity sizing. |
| [`DECISION_JOURNEY.md`](DECISION_JOURNEY.md) | Pre-build | Narrative of how the team arrived at the IMCI / child-survival idea. |
| [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) | Build | Detailed implementation steps, mostly subsumed by `docs/ARCHITECTURE.md`. |
| [`ENHANCEMENT_PLAN.md`](ENHANCEMENT_PLAN.md) | Build | Mid-build enhancement planning, mostly delivered. |
| [`TRACKER.md`](TRACKER.md) | Build | Daily progress tracker / submission checklist. Superseded by GitHub issues + the PR template. |
| [`VIDEO_SCRIPT_v2.md`](VIDEO_SCRIPT_v2.md) | Submission | Earlier draft of the submission video script. Current script is [`../../VIDEO_SCRIPT.md`](../../VIDEO_SCRIPT.md). |
| [`VIDEO_SCRIPT_5MIN.md`](VIDEO_SCRIPT_5MIN.md) | Submission | Five-minute cut of the submission video. |

---

## Why archive instead of delete

Several reasons:

- **Decision provenance.** A reviewer asking *"why did you build it this way?"* gets a complete answer.
- **Reproducibility.** A future maintainer can re-derive the engineering choices from the same starting evidence.
- **Honest engineering.** Hiding the iteration history lies about how the system was built.

If a document here is genuinely wrong (not just out of date), open an issue rather than silently deleting it.
