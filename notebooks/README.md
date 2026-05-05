# Malaika — Notebooks Index

> Every notebook in this directory, what it does, and which ones are *current* vs *reference* vs *superseded*.
>
> **If you are a judge with five minutes:** read **§ Quick start** below — it points to the two notebooks that demonstrate the system end-to-end.

---

## Quick start (the two notebooks judges should run)

| Goal | Notebook | Hardware | Time |
|------|----------|----------|------|
| **Tier 1 — Village clinic server** (live demo of §11 in [`../VIDEO_SCRIPT.md`](../VIDEO_SCRIPT.md)) | [`12_village_clinic_finetuned.ipynb`](./12_village_clinic_finetuned.ipynb) | Kaggle T4 / Colab T4 | ~10 min to live ngrok URL |
| **The fine-tune itself** (the 85% crackle-detection number) | [`06_unsloth_binary_phase1.ipynb`](./06_unsloth_binary_phase1.ipynb) | Kaggle T4 | ~30 min train + eval |

Everything else in this directory is one of: a reference experiment that informed those two, a Colab packaging of the same code, or a superseded earlier attempt kept for reproducibility.

---

## Status taxonomy

| Status | Meaning |
|--------|---------|
| **CURRENT** | Actively used. Demoed in the video or referenced in `SUBMISSION_CHECKLIST.md`. |
| **REFERENCE** | Kept for reproducibility / receipts. Not the canonical version, but the history matters. |
| **SUPERSEDED** | An earlier attempt that was replaced. Kept so the *evolution* is auditable. |
| **PLANNED** | Design document exists in `docs/`; notebook not yet implemented. |

---

## Notebook inventory

### CURRENT — the canonical demo set

| Notebook | What it does | Why it matters |
|----------|--------------|----------------|
| [`06_unsloth_binary_phase1.ipynb`](./06_unsloth_binary_phase1.ipynb) | Fine-tunes Gemma 4 E4B with QLoRA (r=8, 60 steps, anti-overfit) on the **ICBHI 2017** respiratory dataset — binary classification (normal / abnormal) on mel-spectrograms. Patient-level 80/20 split, seed 3407. | The receipt for §9 of the script. Produces the merged adapter hosted at HuggingFace `Vimal0703/malaika-breath-sounds-E4B-merged`. |
| [`08_colab_run_app.ipynb`](./08_colab_run_app.ipynb) | Boots the full **Gradio** form-based app on Colab with the merged model. | One-click smoke test that the full pipeline works on a fresh GPU. |
| [`09_chat_app_colab.ipynb`](./09_chat_app_colab.ipynb) | Conversational IMCI assessment UI on Colab — the chat-style version. | Showcases the agentic conversation flow without the voice layer. |
| [`10_voice_agent_colab.ipynb`](./10_voice_agent_colab.ipynb) | Full **voice agent** on Colab — STT + Gemma + sentence-level TTS, streamed via FastAPI + WebSocket. | The supplementary demo of the agentic voice pipeline (the phone uses Android-native voice, but Colab is where the full Python voice loop lives). |
| [`11_edge_offline_colab.ipynb`](./11_edge_offline_colab.ipynb) | Simulates offline-edge inference on Colab — Gemma 4 E4B + offline Whisper STT, no internet calls during inference. | Proves the *offline-on-edge* claim is reproducible without an Android device. |
| [`12_village_clinic_finetuned.ipynb`](./12_village_clinic_finetuned.ipynb) | Loads the merged fine-tune, wraps it in a **FastAPI** server with `/breath` + `/health` endpoints, exposes via ngrok. The phone or web portal can `POST` a WAV file and get back JSON classification. | **The §11 "Clinic Portal" demo runs against this notebook.** Plan: [`docs/NOTEBOOK_12_VILLAGE_CLINIC_PLAN.md`](../docs/NOTEBOOK_12_VILLAGE_CLINIC_PLAN.md). |

### REFERENCE — kept for the audit trail

| Notebook | What it was | Status |
|----------|-------------|--------|
| [`01_gemma4_feasibility_test.py`](./01_gemma4_feasibility_test.py) | Day 1 feasibility check — verified Gemma 4 E4B loads in 4-bit on a T4, all modalities (text, image, audio-as-spec, video) work, measured VRAM + latency. | **REFERENCE.** Foundational receipt — answers *"did Gemma 4 actually fit and run before we built anything?"* Yes. |
| [`04_day4_real_data_test.py`](./04_day4_real_data_test.py) | Day 4 — first end-to-end spectrogram pipeline test on real ICBHI data. Established the audio→mel-spec→vision-prompt path that notebook 06 then fine-tuned. | **REFERENCE.** The blueprint that 06 industrialised. |

### SUPERSEDED — earlier attempts, kept for reproducibility

| Notebook | What it was | Replaced by |
|----------|-------------|-------------|
| [`02_finetune_breath_sounds.ipynb`](./02_finetune_breath_sounds.ipynb) + `.py` | Fine-tune v5 (early version, multi-class crackle/wheeze/normal/both, overfit issues — loss crashed too fast). | `06_unsloth_binary_phase1.ipynb` — anti-overfit settings (LR 5e-5, 60 steps, weight-decay 0.1), binary task (matches IMCI's actual question: "abnormal yes/no?"). |
| [`03_end_to_end_test.ipynb`](./03_end_to_end_test.ipynb) + `.py` | First integration test — proved code + model + prompts + guards + protocol = working assessment, end-to-end. | `12_village_clinic_finetuned.ipynb` — production version with FastAPI + ngrok exposure. |
| [`06_finetune_audio_features.ipynb`](./06_finetune_audio_features.ipynb) | **Path 2** — alternative approach that fine-tuned on extracted audio features as text (MFCC summaries, spectral statistics) rather than spectrogram images. | `06_unsloth_binary_phase1.ipynb` — the spectrogram-vision path won; it leverages Gemma's existing vision encoder rather than encoding audio descriptively. We kept this so anyone reproducing can see why we picked the vision path. |
| [`07_unsloth_E2B_edge.ipynb`](./07_unsloth_E2B_edge.ipynb) | E2B edge-deployment experiment with Unsloth. | Folded into `11_edge_offline_colab.ipynb` and the production Flutter app's LiteRT-LM runtime. |
| [`kaggle_e2e_results.ipynb`](./kaggle_e2e_results.ipynb) | Kaggle results dump from Apr 14 — early-week E2E run output saved with code. | `03_end_to_end_test.ipynb` (cleaner version) → `12_village_clinic_finetuned.ipynb` (production). |

### PLANNED — design exists, implementation pending

| Notebook | Plan | Why it matters |
|----------|------|----------------|
| `13_base_vs_finetuned_comparison.ipynb` | [`docs/NOTEBOOK_13_BASE_VS_FINETUNED_PLAN.md`](../docs/NOTEBOOK_13_BASE_VS_FINETUNED_PLAN.md) | The receipt for §9's claim that *base Gemma cannot read mel-spectrograms as clinical signal.* Runs base `gemma-4-E4B-it` and `Vimal0703/malaika-breath-sounds-E4B-merged` on the same held-out set, side by side. ~3 hours to implement. |

---

## Why we kept the superseded ones

Two reasons.

**One — reproducibility.** A fine-tune is the sum of every decision that came before it. Notebook 02's overfit failure is *why* notebook 06 has anti-overfit settings. Notebook `06_finetune_audio_features` is *why* the spectrogram path was chosen over the audio-features-as-text path. Deleting them deletes the *why*.

**Two — anti-marketing.** `REASONS_WE_WILL_FAIL.md` says we don't hide the failure modes. The superseded notebooks are the same principle applied to engineering history: we tried things, they didn't work, here's what we kept and what we replaced. Anyone forking this repo can see the path, not just the destination.

If you are reproducing the fine-tune, **only** run `06_unsloth_binary_phase1.ipynb`. The others are not part of the pipeline.

---

## Reproducing the headline numbers

| Claim in the video | Notebook that produces it | Hardware |
|--------------------|---------------------------|----------|
| 85% crackle detection on held-out patients | `06_unsloth_binary_phase1.ipynb` Cell 14 | Kaggle T4 (free tier works) |
| Live `/breath` endpoint a phone can call | `12_village_clinic_finetuned.ipynb` Cell 7 | Kaggle T4 + ngrok |
| Full IMCI assessment via voice on a GPU | `10_voice_agent_colab.ipynb` | Colab T4 |
| Offline edge inference (Whisper + Gemma) | `11_edge_offline_colab.ipynb` | Colab T4 |
| Phone-only offline assessment | *not in this directory* — see `malaika_flutter/` | Samsung A53 (or any Android with ≥4 GB RAM, GPU ≥2.6 GB) |

---

## How the web portal calls notebook 12

```
  Browser (nurse)              Vercel / localhost:3000          Kaggle / Colab T4
  ─────────────────            ───────────────────────          ───────────────────
   /portal
   ↓ (records WAV in browser)
   POST /api/breath  ────►   Next.js route handler
                              · checks session cookie
                              · reads BREATH_API_URL env
                              · forwards FormData
                              ─── POST {URL}/breath ──────►  notebook 12
                                                                  · loads Vimal0703/malaika-breath-sounds-E4B-merged
                                                                  · FastAPI: /breath + /health
                                                                  · ngrok tunnel → public URL
                                                                  · second Gemma pass = clinical note
                              ◄── JSON {abnormal, conf, note} ───
                              ◄── parsed JSON
   result card ◄────
```

The web app proxies *server-side* — `BREATH_API_URL` is never exposed to the browser. Notebook 12 has no auth of its own; the proxy and its session cookie are the only gate. See [`web/app/api/breath/route.ts`](../web/app/api/breath/route.ts).

---

## Required Kaggle secrets

For any notebook that loads `Vimal0703/malaika-breath-sounds-E4B-merged` or exposes a server:

| Secret | Where to set | What it's for |
|--------|--------------|---------------|
| `HF_TOKEN` | Kaggle → Add-ons → Secrets | Read access to the merged HF model |
| `NGROK_TOKEN` | Kaggle → Add-ons → Secrets | Public URL for the FastAPI server (notebook 12) |

For Colab notebooks (08, 09, 10, 11), the same tokens go in *Colab → Tools → Secrets*.

---

*Last updated: 2026-05-04. The plan is to keep this index current — every new notebook gets a row, every superseded one gets re-classified, nothing is silently deleted.*
