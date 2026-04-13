# prompts/ — Prompt Engineering Skill

> Prompts are first-class code. Versioned, typed, registered, tested. Never hardcoded.

---

## What This Module Does

Every text prompt that Gemma 4 receives is a `PromptTemplate` object registered in `PromptRegistry`. This module owns:

- **Prompt definition**: System prompts, user templates, output schemas
- **Prompt rendering**: Filling templates with variables, attaching media
- **Prompt versioning**: Every prompt has a semantic version for tracking changes
- **Prompt registry**: Central lookup by name so service code never inlines prompt strings

## What This Module Does NOT Do

- Does NOT call inference (that's `inference.py`)
- Does NOT parse model output (that's `guards/output_validator.py`)
- Does NOT contain clinical logic (that's `imci_protocol.py`)
- Does NOT store or access media files (that's `guards/input_guard.py`)

---

## Rules

### R1: Every Prompt Gets a PromptTemplate
No prompt string literals in service code. Ever. If you need Gemma 4 to do something, create a `PromptTemplate` here and register it.

```python
# CORRECT — in malaika/vision.py
prompt = PromptRegistry.get("breathing.detect_chest_indrawing")
messages = prompt.render_multimodal(media={"image": str(path)})

# WRONG — in malaika/vision.py
messages = [{"role": "user", "content": "Is there chest indrawing?"}]
```

### R2: Structured Output Always
Every clinical prompt MUST request JSON output with a defined schema. Free-form text responses are only allowed for treatment generation and conversational responses.

### R3: Temperature 0.0 for Clinical
All perception prompts (vision, audio, assessment) use `temperature=0.0`. Only `treatment.py` and `speech.py` may use higher temperatures.

### R4: Injection Defense is Automatic
The `PromptTemplate.injection_defense` field is appended to every system prompt automatically. Never remove it. Never override it with empty string.

### R5: Max Tokens Tuned Per Task
Don't waste inference time. A breathing rate count needs ~100 tokens, not 512.

| Task Type | Max Tokens |
|-----------|-----------|
| Binary assessment (yes/no + confidence) | 100-150 |
| Multi-field assessment (indrawing, wheeze) | 150-200 |
| Treatment generation | 400-500 |
| Conversational response | 200-300 |

### R6: Version Bumps
- **Patch** (1.0.1): Wording tweaks, no output format change
- **Minor** (1.1.0): New fields in output, added context
- **Major** (2.0.0): Different approach, different output schema

### R7: One File Per IMCI Domain
Breathing prompts in `breathing.py`. Danger sign prompts in `danger_signs.py`. Never mix domains.

---

## How to Add a New Prompt

1. Open the correct domain file (e.g., `breathing.py`)
2. Create a `PromptTemplate` with all fields
3. Register it: `MY_PROMPT = PromptRegistry.register(PromptTemplate(...))`
4. Add a test in `tests/test_prompts.py` that verifies rendering
5. Add an entry to the inventory table in `docs/PROMPT_ENGINEERING.md`

---

## File Inventory

| File | Domain | Prompts |
|------|--------|---------|
| `base.py` | — | `PromptTemplate` base class |
| `__init__.py` | — | `PromptRegistry` central lookup |
| `system.py` | All | Malaika persona system prompt |
| `danger_signs.py` | Danger signs | Alertness, convulsions, ability to drink |
| `breathing.py` | Breathing | Rate from video, chest indrawing, breath sounds |
| `diarrhea.py` | Diarrhea | Dehydration signs, skin pinch, duration |
| `fever.py` | Fever | Duration, malaria risk, measles |
| `nutrition.py` | Nutrition | Visible wasting, edema, MUAC |
| `heart.py` | Heart MEMS | Heart sounds, BPM estimation |
| `treatment.py` | Treatment | Generate instructions in local language |
| `speech.py` | Speech | Understand caregiver intent from audio |
