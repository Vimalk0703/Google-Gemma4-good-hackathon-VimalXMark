# Engineering documentation

Welcome to Malaika's engineering docs. This is the **technical** documentation set; for the user-facing pitch and project structure see the top-level [`README.md`](../README.md), and for AI agents see [`../AGENTS.md`](../AGENTS.md).

These documents are the law of this project. Read them before you write code.

---

## Read in this order

| # | Document | Read when |
|---|----------|-----------|
| 1 | [`ARCHITECTURE.md`](ARCHITECTURE.md) | Always first — system architecture, component boundaries, data flow, deployment topology. |
| 2 | [`ENGINEERING_PRINCIPLES.md`](ENGINEERING_PRINCIPLES.md) | Before writing any code — design principles, error-handling philosophy, performance standards. |
| 3 | [`SECURITY.md`](SECURITY.md) | Before touching anything that handles user input, model output, or PHI. The three-layer guard pipeline is mandatory. |
| 4 | [`PROMPT_ENGINEERING.md`](PROMPT_ENGINEERING.md) | Before changing or adding any prompt to Gemma 4 — the `PromptTemplate` pattern is non-negotiable. |
| 5 | [`TESTING_STRATEGY.md`](TESTING_STRATEGY.md) | Before writing tests — testing pyramid, coverage targets, medical-accuracy validation against the 21 golden IMCI scenarios. |
| 6 | [`DEVELOPMENT.md`](DEVELOPMENT.md) | When setting up your environment — code style, type hints, git workflow, commit conventions. |

---

## Reference documents

| Document | Purpose |
|----------|---------|
| [`FINETUNING_ROADMAP.md`](FINETUNING_ROADMAP.md) | LoRA fine-tuning strategy: PEFT v1–v5 history and Unsloth-native pivot for the breath-sound classifier. |
| [`NOTEBOOK_12_VILLAGE_CLINIC_PLAN.md`](NOTEBOOK_12_VILLAGE_CLINIC_PLAN.md) | Plan for the village clinic notebook (Tier 1 server with fine-tuned breath classifier + AI clinical note). |
| [`NOTEBOOK_13_BASE_VS_FINETUNED_PLAN.md`](NOTEBOOK_13_BASE_VS_FINETUNED_PLAN.md) | Plan for the base vs fine-tuned comparison notebook. |
| [`SESSION_LOG.md`](SESSION_LOG.md) | Detailed development journal: steps, findings, decisions, what worked, what didn't. |

---

## By audience

### If you are a contributor

1. [`ARCHITECTURE.md`](ARCHITECTURE.md)
2. [`ENGINEERING_PRINCIPLES.md`](ENGINEERING_PRINCIPLES.md)
3. [`DEVELOPMENT.md`](DEVELOPMENT.md)
4. [`TESTING_STRATEGY.md`](TESTING_STRATEGY.md)
5. Whichever specific doc covers the area you're touching (security, prompts, fine-tuning).

### If you are a security reviewer

1. [`SECURITY.md`](SECURITY.md) — technical guard architecture
2. [`../SECURITY.md`](../SECURITY.md) — vulnerability disclosure policy
3. [`ARCHITECTURE.md`](ARCHITECTURE.md) — to understand attack surface
4. [`PROMPT_ENGINEERING.md`](PROMPT_ENGINEERING.md) — for prompt-injection defence

### If you are a clinical reviewer

1. [`../README.md`](../README.md) — what the system actually does
2. [`ARCHITECTURE.md`](ARCHITECTURE.md) — what code decides vs what Gemma 4 decides
3. [`TESTING_STRATEGY.md`](TESTING_STRATEGY.md) — the 21 golden IMCI scenarios and how they validate clinical accuracy
4. [`../malaika/imci_protocol.py`](../malaika/imci_protocol.py) — every WHO threshold cited to the IMCI manual

### If you are an AI coding/judging agent

Read [`../AGENTS.md`](../AGENTS.md) first — it gives you the file map, hard rules, and the verification quick reference. Then return here for the technical depth.

---

## Out-of-date check

If anything in these documents contradicts the code, **the code is correct** and the doc is wrong. Open a PR to fix the doc. Do not bend the code to match a stale document.
