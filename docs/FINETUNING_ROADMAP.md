# Malaika — Fine-Tuning Roadmap

> Base Gemma 4 E4B handles all IMCI assessment tasks at baseline level.
> Fine-tuning targets specific clinical accuracy improvements.

---

## Current State: Base Model Capabilities

| Task | Base Model Performance | Evidence |
|------|----------------------|----------|
| Child alertness (photo) | "Baby lying on white surface, crying, alert" | Colab T4 test, 47s |
| Chest indrawing (photo) | "Cannot determine from static photo" — honest limitation | Colab T4 test |
| Dehydration signs (photo) | "Eyes not sunken, child appears well-hydrated" | Colab T4 test |
| Nutrition/wasting (photo) | "Well-nourished, no visible signs of wasting" | Colab T4 test |
| Caregiver answer parsing | Correctly extracts findings from natural language | LLM parser, all steps |
| Treatment generation | Generic health advice, needs WHO-specific training | Repetition issues observed |
| Spectrogram classification | 25% baseline (all normal), needs fine-tuning | Notebook 04 |

**Verdict:** Base model is sufficient for hackathon demo. Fine-tuning improves accuracy for production use.

---

## Completed Fine-Tuning: Breath Sound Spectrograms

| Detail | Value |
|--------|-------|
| **Model** | `Vimal0703/malaika-breath-sounds-E4B-merged` |
| **Method** | Unsloth QLoRA, r=8/r=32, vision+language layers |
| **Dataset** | ICBHI 2017 (920 recordings, patient-level splits) |
| **Task** | Binary: normal vs abnormal breath sounds |
| **Best Result** | 40% overall, 85% crackle detection (v5) |
| **Iterations** | 5 (documented in notebooks 02, 05, 06) |
| **Adapter** | 82 MB, saved in `adapters/` |
| **Key Learning** | Vision encoder (SigLIP) is frozen — LoRA only adapts language attention |

### Innovation
Audio → mel-spectrogram PNG → Gemma 4 vision fine-tuning.
Bypasses Gemma 4's lack of native audio support.

---

## Planned Fine-Tuning: Datasets to Prepare

### 1. Chest Indrawing Detection
- **Goal:** Detect subcostal chest indrawing from chest photos/videos
- **Dataset sources:**
  - WHO IMCI training materials (public domain images)
  - Open-access pediatric respiratory distress images
  - Synthetic: annotated video frames from clinical teaching
- **Labels:** indrawing_present (true/false), severity (mild/moderate/severe)
- **Expected improvement:** Base model can't assess from static photo → fine-tuned model detects from single frame
- **Metric:** Sensitivity, specificity vs clinical ground truth

### 2. Jaundice / Skin Color Assessment
- **Goal:** Detect neonatal jaundice, cyanosis, pallor from skin photos
- **Dataset sources:**
  - Open dermatology datasets (diverse skin tones)
  - Neonatal jaundice grading images (Kramer zones)
  - ISIC skin datasets (filtered for pediatric)
- **Labels:** jaundice (none/mild/moderate/severe), cyanosis (true/false), pallor (true/false)
- **Expected improvement:** Base model describes color but can't grade severity → fine-tuned model grades Kramer zones
- **Metric:** Agreement with bilirubin-confirmed jaundice levels

### 3. Visible Wasting / Malnutrition
- **Goal:** Detect severe acute malnutrition (SAM) from body photos
- **Dataset sources:**
  - UNICEF/WHO malnutrition assessment images
  - Community-based management of acute malnutrition (CMAM) training materials
  - Open pediatric nutrition datasets
- **Labels:** normal, moderate_malnutrition, severe_malnutrition, edema
- **Expected improvement:** Base model says "well-nourished" for most → fine-tuned detects muscle wasting patterns
- **Metric:** Sensitivity for SAM detection vs MUAC ground truth

### 4. Dehydration Signs
- **Goal:** Detect sunken eyes, skin turgor from face/body photos
- **Dataset sources:**
  - WHO ORS training materials
  - Clinical dehydration assessment images
  - Annotated pediatric emergency datasets
- **Labels:** no_dehydration, some_dehydration, severe_dehydration
- **Expected improvement:** Base model checks eyes only → fine-tuned assesses multiple signs
- **Metric:** Agreement with clinical dehydration scale

### 5. WHO Treatment Protocol
- **Goal:** Generate accurate WHO IMCI treatment plans with correct dosages
- **Dataset sources:**
  - WHO IMCI chart booklet (public domain, all treatment tables)
  - WHO Essential Medicines dosage tables
  - IMCI case management exercises with model answers
- **Format:** Instruction fine-tuning (classification → treatment text)
- **Labels:** Input: age + classifications + urgency → Output: correct WHO treatment plan
- **Expected improvement:** Generic advice → precise WHO dosages and follow-up schedules
- **Metric:** Treatment plan accuracy vs WHO reference (human evaluation)

---

## Fine-Tuning Infrastructure

| Resource | Status |
|----------|--------|
| **GPU** | Kaggle T4 (free), Colab T4 (free) |
| **Framework** | Unsloth QLoRA (proven with breath sounds) |
| **Training time** | ~15-45 min per adapter on T4 |
| **Adapter size** | ~10-80 MB per adapter |
| **Evaluation** | Golden scenarios + per-class accuracy |

### Architecture Decision
- **Base model** for demo (all general tasks)
- **LoRA adapters** loaded per-task for production accuracy
- **Merged model** for edge deployment (single model, no adapter swap)

---

## Timeline

| Week | Fine-Tuning Focus |
|------|-------------------|
| Apr 14-18 | Document datasets, prepare data scripts |
| Apr 19-25 | Chest indrawing + jaundice fine-tuning |
| Apr 26-May 2 | Wasting + dehydration fine-tuning |
| May 3-9 | Treatment protocol fine-tuning + merge all adapters |
| May 10-18 | Final evaluation, writeup numbers, submit |

---

*Last updated: April 16, 2026*
