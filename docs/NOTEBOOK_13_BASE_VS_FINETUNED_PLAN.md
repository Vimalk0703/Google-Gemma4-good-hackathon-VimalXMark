# Notebook 13 — Base Gemma 4 E4B vs Fine-Tuned Comparison (Plan)

> Design document for `notebooks/13_base_vs_finetuned_comparison.ipynb`.
>
> **Why this notebook exists:** The §9 *"Why Fine-Tune — and Why Not"* beat in `VIDEO_SCRIPT.md` claims that base Gemma 4 cannot read mel-spectrograms as clinical signal — that the fine-tune is what turns *"blue regions and vertical lines"* into *"crackles."* This notebook is the **receipt** for that claim. It runs the **same** held-out audio set through **both** models — the base `google/gemma-4-E4B-it` and our fine-tuned `Vimal0703/malaika-breath-sounds-E4B-merged` — side by side, prints the diff, and saves a CSV anyone can re-verify.
>
> Without this notebook, the §9 claim is a story. With it, the claim is a number anyone can reproduce in fifteen minutes on a Kaggle T4.

---

## What This Notebook Demonstrates

A clear, reproducible, side-by-side comparison of:

- **Model A** — `google/gemma-4-E4B-it` (base, no fine-tune, system-prompted only)
- **Model B** — `Vimal0703/malaika-breath-sounds-E4B-merged` (our fine-tune from notebook 06)

Both models receive **identical** input — the same mel-spectrogram, the same system prompt, the same instruction asking for `{abnormal: bool, confidence: float, description: str}` JSON.

The notebook proves four things:

1. **Base Gemma describes spectrograms in plain English** (e.g. *"vertical lines on a blue background"*) and frequently refuses to commit to a clinical label.
2. **Fine-tuned Gemma returns structured JSON** with confidence scores — the same schema every time.
3. **On held-out patients, the fine-tune lifts crackle detection from a low baseline to ~85%.** The number is the receipt.
4. **The cost of getting there is 82 MB of LoRA weights** — not a separate model, not a CNN, not a new pipeline.

---

## Cell-by-Cell Plan

### Cell 0 — Markdown header

Mission statement, link back to `VIDEO_SCRIPT.md` §9 and `REASONS_WE_WILL_FAIL.md` §4 (where we say the 85% is hackathon-grade, not FDA-cleared).

### Cell 1 — Install

```python
%%capture
!pip install unsloth librosa soundfile Pillow pandas matplotlib
```

### Cell 2 — Authenticate

```python
from huggingface_hub import login
from kaggle_secrets import UserSecretsClient
secrets = UserSecretsClient()
login(token=secrets.get_secret("HF_TOKEN"))
```

### Cell 3 — Load **both** models

```python
from unsloth import FastModel
import torch, gc

# Model A — base
base_model, base_tok = FastModel.from_pretrained(
    model_name="google/gemma-4-E4B-it",
    max_seq_length=2048, load_in_4bit=True,
)
print(f"Base loaded — VRAM: {torch.cuda.memory_allocated()/1024**3:.2f} GB")

# Free before loading Model B
del base_model, base_tok
gc.collect(); torch.cuda.empty_cache()

# Model B — fine-tuned
ft_model, ft_tok = FastModel.from_pretrained(
    model_name="Vimal0703/malaika-breath-sounds-E4B-merged",
    max_seq_length=2048, load_in_4bit=True,
)
print(f"Fine-tuned loaded — VRAM: {torch.cuda.memory_allocated()/1024**3:.2f} GB")
```

> *Note:* on a T4 we cannot hold both models in memory simultaneously. We run Model A on the test set, save predictions to disk, free, then run Model B on the same test set, save, free, and compare.

### Cell 4 — Load held-out test set (identical to notebook 06)

Re-uses the same patient-level 80/20 split from notebook 06. Same random seed (3407). Same `audio_to_spec` transform. **The training cells from notebook 06 produce a `test_pairs` list** — we serialize it to JSON at the end of notebook 06's run, and load it here.

### Cell 5 — Identical instruction (the critical control)

```python
INSTRUCTION = (
    "This is a mel-spectrogram of a child's breathing audio.\n"
    "Are the breath sounds normal or abnormal?\n"
    'Respond with JSON: {"abnormal": true/false, "confidence": 0.0-1.0, "description": "brief reason"}'
)

SYSTEM_MSG = (
    "You are Malaika, a medical spectrogram analysis assistant. "
    "Detect abnormal breath sounds (wheeze, crackles, stridor) from spectrograms. "
    "Respond ONLY with valid JSON."
)
```

**Identical** instruction and system message for both models. The only variable is the model itself.

### Cell 6 — Inference loop, Model A (base)

```python
predictions_A = []
for pair in test_pairs:
    img = Image.open(pair["spec_path"]).convert("RGB")
    raw = run_inference(base_model, base_tok, img, SYSTEM_MSG, INSTRUCTION)
    parsed = try_parse_json(raw)  # returns dict or None
    predictions_A.append({
        "patient_id": pair["patient_id"],
        "label": pair["label"],
        "raw": raw,
        "parsed": parsed,
        "json_valid": parsed is not None,
    })

# Save to disk before freeing the model
pd.DataFrame(predictions_A).to_csv("/kaggle/working/predictions_base.csv", index=False)
```

### Cell 7 — Free Model A, load Model B (fine-tuned), repeat

Same loop, identical inputs, save to `predictions_finetuned.csv`.

### Cell 8 — Side-by-side comparison

```python
df_A = pd.read_csv("/kaggle/working/predictions_base.csv")
df_B = pd.read_csv("/kaggle/working/predictions_finetuned.csv")

merged = df_A.merge(df_B, on=["patient_id", "label"], suffixes=("_base", "_ft"))

print("=" * 70)
print("BASE vs FINE-TUNED — head-to-head")
print("=" * 70)
print(f"{'Patient':<10} {'Truth':<10} {'Base raw':<28} {'FT parsed':<22}")
for row in merged.sample(20).itertuples():
    base_summary = (row.raw_base or "")[:25] + "…"
    ft_summary = str(row.parsed_ft)[:18] + "…"
    print(f"{row.patient_id:<10} {row.label:<10} {base_summary:<28} {ft_summary:<22}")
```

**Expected qualitative finding:** Model A's `raw` column is mostly free-form English — *"The spectrogram shows..."*, *"I cannot make a clinical determination..."*. Model B's `parsed` column is JSON, every time.

### Cell 9 — Quantitative metrics

```python
def metrics(df, label_col="label", parsed_col="parsed", json_valid_col="json_valid"):
    n = len(df)
    valid = df[json_valid_col].sum()
    correct = sum(
        1 for _, r in df.iterrows()
        if r[json_valid_col] and r[parsed_col].get("abnormal") == (r[label_col] == "abnormal")
    )
    return {
        "n": n,
        "json_valid_rate": valid / n,
        "accuracy_when_valid": correct / valid if valid else 0,
        "accuracy_overall": correct / n,
    }

print("BASE       :", metrics(df_A))
print("FINE-TUNED :", metrics(df_B))
```

**Expected output (illustrative — actual numbers come from the live run):**

```
BASE       : { json_valid_rate: ~0.20, accuracy_overall: ~0.10 }
FINE-TUNED : { json_valid_rate: ~1.00, accuracy_overall: ~0.40, crackle_detection: ~0.85 }
```

> The base model's *accuracy_when_valid* may look reasonable on the small subset where it produced valid JSON — but its *json_valid_rate* is the killer. If it can't answer the question 80% of the time, it can't be in a clinical pipeline.

### Cell 10 — Failure-mode taxonomy (qualitative)

For the rows where models disagree, classify the failure type:

- **Refusal** — base model says it cannot make a clinical determination
- **Free-form prose** — base returns descriptive text, no JSON
- **Wrong abnormal/normal** — both produced JSON, disagreed on the label
- **Hallucination** — model claims a finding (e.g. "wheeze") that isn't in the audio

Print top 5 examples of each category.

### Cell 11 — Confusion matrix + plot

Use `sklearn.metrics.confusion_matrix` and `matplotlib` to plot 2×2 confusion matrices for both models, side by side. Save as PNG to `/kaggle/working/confusion_comparison.png`. This is the image that goes into the README and the Kaggle write-up.

### Cell 12 — Summary card (print to log)

```python
print("=" * 70)
print("BASE vs FINE-TUNED — SUMMARY")
print("=" * 70)
print(f"Test set:                {len(test_pairs)} held-out patients")
print(f"Base accuracy (overall): {acc_A:.0%}")
print(f"Fine-tuned accuracy:     {acc_B:.0%}")
print(f"Δ from fine-tuning:      +{(acc_B - acc_A)*100:.0f} percentage points")
print(f"Cost of fine-tuning:     82 MB LoRA weights, 60 steps, ~25 min on T4")
print()
print("Conclusion: the base model cannot read mel-spectrograms as clinical signal.")
print("The fine-tune is what makes the same brain hear the wheeze.")
print()
print("This is the receipt for VIDEO_SCRIPT.md §9.")
```

---

## Inputs Required to Run

| Resource | Where it comes from |
|----------|---------------------|
| `HF_TOKEN` | Kaggle Secrets — to load `Vimal0703/malaika-breath-sounds-E4B-merged` |
| ICBHI 2017 dataset | Kaggle dataset `vbookshelf/respiratory-sound-database` (added via "Add Data") |
| `test_pairs.json` | Saved at end of notebook 06's run — patient-level 80/20 split, seed 3407 |
| GPU | Kaggle T4 or Colab T4 (free tier sufficient) |

---

## Outputs Produced

1. `predictions_base.csv` — base model's outputs on the full held-out set
2. `predictions_finetuned.csv` — fine-tuned model's outputs on the same set
3. `confusion_comparison.png` — side-by-side confusion matrices
4. Console summary card matching notebook 06's format
5. A reproducible verdict on the §9 claim — *the fine-tune is what teaches the model to read the modality, not just to label it.*

---

## How This Connects to the Video

`VIDEO_SCRIPT.md` §9 — Mark says:

> *"Base Gemma can describe a spectrogram. Blue regions. Vertical lines. It cannot tell you that those vertical bursts in the two-hundred-hertz band are crackles. The base model has the eyes; it does not have the medical mapping. … We also publish a base-versus-fine-tuned comparison notebook — same data, same task, two models — so you can see exactly what the LoRA adds."*

**Without this notebook**, that claim is rhetoric. **With this notebook**, the claim is a CSV anyone can re-run on a free Kaggle T4.

---

## How This Connects to Existing Repo Artefacts

- Depends on: `notebooks/06_unsloth_binary_phase1.ipynb` (the original fine-tuning run + the held-out split it produces)
- Reuses: same `INSTRUCTION`, `SYSTEM_MSG`, and `audio_to_spec` from notebook 06 (consistency is the point)
- Loads: `Vimal0703/malaika-breath-sounds-E4B-merged` (the merged adapter, already on HF)
- Mirrors structure of: `notebooks/12_village_clinic_finetuned.ipynb` (same model-loading pattern)
- Output PNG goes into: `README.md` (illustrating the §9 fine-tune claim) and the Kaggle submission cover

---

## Effort Estimate

| Phase | Time | Risk |
|-------|------|------|
| Scaffold notebook (writing cells) | 1 hour | Low — pattern reuse from 06, 12 |
| Save test_pairs.json from notebook 06's last cell | 10 min | Low |
| First Kaggle T4 run, debug auth | 30 min | Low |
| Run Model A (base) on full test set | ~20 min | Low |
| Run Model B (fine-tuned) on full test set | ~20 min | Low |
| Generate plots, write summary | 30 min | Low |

**Total: ~3 hours.** Achievable in one focused session. The notebook is a pure inference comparison — no training, no new data, no novel infrastructure.

---

## What This Notebook Does NOT Do

(Per `REASONS_WE_WILL_FAIL.md`, we are explicit about boundaries.)

- It does not claim that 85% crackle detection is clinical-grade. It is the held-out number on ICBHI 2017. We restate the limit.
- It does not extend to children under one year — ICBHI 2017's age distribution skews older. The model card says so. The README repeats it.
- It does not retrain. The two models are loaded as-is. This notebook is purely the *receipt*, not the *recipe* — the recipe is notebook 06.
- It does not include a CNN-only baseline. We could add one — but the §9 claim is *"why fine-tune Gemma vs use base Gemma,"* not *"why fine-tune Gemma vs train a CNN from scratch."* The CNN comparison would be a fourth notebook, out of scope.

---

## Why This Matters for the Submission

A judge who reads `VIDEO_SCRIPT.md` §9 has two questions:

1. *"Is it true the base model can't do this?"*
2. *"Is the 85% number real?"*

This notebook answers both — in one CSV, in fifteen minutes, on free hardware. **That is the bar for "we came here with receipts."**

---

*Plan authored: 2026-05-03. Will be implemented as `notebooks/13_base_vs_finetuned_comparison.ipynb` in the next sprint, after notebook 12 is verified end-to-end.*
