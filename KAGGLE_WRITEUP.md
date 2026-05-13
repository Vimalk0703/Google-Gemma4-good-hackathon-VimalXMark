# Malaika — Kaggle Writeup (paste-ready)

> This file maps directly to the Kaggle Writeup form for **The Gemma 4 Good Hackathon**.
> Each section below corresponds to a field in the form. Copy and paste in order.
>
> **Submission deadline:** May 18, 2026, 7:59 PM EDT.
> **Word limit on Project Description:** 1,500 words (this draft: ~1,450).

---

## 1. Title  *(form field — max 80 characters)*

```
Malaika — A WHO child-survival assistant on a $60 phone, fully offline.
```

*(70 characters.)*

---

## 2. Subtitle  *(form field — max 140 characters)*

```
Open-source, multilingual, multimodal. Powered end-to-end by Gemma 4 — on every phone the village mother already owns. Apache 2.0.
```

*(133 characters.)*

---

## 3. Submission Track  *(form field — pick one)*

**Impact Track → Health & Sciences.**

*(Primary. The project is auto-eligible for the Main Track on overall merit, and for the Special Technology Track on Unsloth — we fine-tuned Gemma 4 E4B with Unsloth QLoRA — and LiteRT — the phone runs Gemma 4 E2B through LiteRT-LM.)*

---

## 4. Card and Thumbnail Image  *(form field — 560 × 280)*

Required dimensions: **560 × 280** (the form note overrides the 1280×720 mentioned elsewhere in the Kaggle rules — go with what the form says).

**Design brief for the editor / designer:**

- **Composition:** Hands of a mother holding a sleeping child, half in shadow. The child's face is calm. Mother's other hand holds a budget Android phone — Malaika's amber/gold wordmark glowing on screen. Background: dawn light through a corrugated-iron window. Warmth, not despair.
- **Top-third overlay (sans-serif, white):** *"Malaika — Angel, in Swahili."*
- **Bottom-third overlay:** *"Open-source WHO IMCI assistant. Gemma 4. Offline. On any phone."*
- **Format:** JPG, ≤ 1 MB, 560 × 280 pixels (Kaggle thumbnail aspect ratio).
- **Avoid:** clinical sterility, dramatic suffering, AI-generated faces. Use real photography or a posed shot with a model + signed release.

---

## 5. Media Gallery  *(form field — YouTube videos)*

Attach in this order:

1. **The Kaggle submission video (≤ 3 minutes).** Short cut: **[https://youtu.be/Gf415IgJr0s](https://youtu.be/Gf415IgJr0s)**
   *⚠️ Verify duration is ≤ 3:00 before attaching. If the cut is 3:30, a 30-second trim is needed.*

2. **Full storytelling film (12 minutes).** *Linked in the writeup body as "must-watch for the full picture."* **[https://youtu.be/2p932LTc_wE](https://youtu.be/2p932LTc_wE)**

3. **Full working app demo on Samsung A53.** **[https://youtu.be/yV8jBH6-_I0](https://youtu.be/yV8jBH6-_I0)**

---

## 6. Project Links  *(form field — Attachments → Project Links)*

Kaggle's Project Link entry accepts up to **200 words of description per link**. The seven blocks below are paste-ready — copy the label, the URL, and the description into each *Add a link* form. They are ordered by what a judge should open first.

---

### Link 1 · Live demo · open clinical portal

**URL:** https://malaika-delta.vercel.app/

**Description** *(≈200 words):*

> The Tier-1 clinical portal — open, no login, no signup, no email gate. The cleanest five-minute proof of the submission. Visit the page and click *Load sample audio*: the bundled ICBHI 2017 clip (patient 104, anterior-left auscultation, Littmann 3200 stethoscope) loads into the upload box without any download step. Click *Analyze breath sounds* and the full Tier-1 pipeline executes in roughly seven seconds — the 22,050 Hz mono WAV is converted server-side into a mel-spectrogram, classified by our fine-tuned Gemma 4 E4B + LoRA model, and rendered as a result card showing the classification, model confidence, latency, and the **AI Clinical Note** — a 3-4 sentence reasoning paragraph written by the same Gemma 4 model in a senior-nurse-mentoring-a-junior-colleague voice, grounded in WHO IMCI and naming the next deterministic protocol step. The portal is built in Next.js 16 with browser-native MediaRecorder for live recording (WAV is encoded in the browser before leaving the page) and a live connection-health probe. Decision support, never diagnosis. The on-device Tier-0 phone story sits beside this in the demo video below.

---

### Link 2 · Public code repository · GitHub

**URL:** https://github.com/Vimalk0703/Google-Gemma4-good-hackathon-VimalXMark

**Description** *(≈200 words):*

> The source of truth — Apache 2.0 end-to-end. Flutter Android app (`malaika_flutter/`), Python service with 12-skill agentic architecture (`malaika/`), Unsloth fine-tuning notebook (`notebooks/06_unsloth_binary_phase1.ipynb`), village-clinic FastAPI server (`notebooks/12_village_clinic_finetuned.ipynb`), Next.js 16 web portal (`web/`). Start at the top of `README.md` — the **"Evidence at a glance"** table maps every load-bearing claim in this submission to a specific file path, so any single claim can be verified in two clicks. Engineering rigor judges can run themselves: 104+ passing tests including 21 WHO IMCI golden scenarios (`tests/`), three-layer security guards in `malaika/guards/` (input validation → content filter → output schema), 31 versioned `PromptTemplate` objects in `malaika/prompts/`, and per-step observability traces in `malaika/observability/`. CI is green on every PR (Python ruff + mypy strict + pytest, Flutter analyze, Web lint + build, Vercel preview). All deterministic WHO IMCI classification is hard-coded thresholds (`imci_protocol.dart` / `imci_protocol.py`), never LLM output — we do not let an AI decide whether a child lives or dies. The medicine belongs to the World Health Organization; the AI's job is the human part.

---

### Link 3 · Fine-tuned model · Hugging Face *(Unsloth track)*

**URL:** https://huggingface.co/Vimal0703/malaika-breath-sounds-E4B-merged

**Description** *(≈200 words):*

> The **Special Technology · Unsloth** track submission. Gemma 4 E4B fine-tuned with **Unsloth QLoRA** (`FastModel`, 4-bit, r=8, 60 steps, seed 3407, anti-overfit configuration) on the ICBHI 2017 Respiratory Sound Database — 920 recordings, 6,898 cycles, 126 patients. The audio → mel-spectrogram → vision-encoder pipeline turns auscultation recordings into images that Gemma 4's SigLIP encoder reads as clinical signal. Methodology choice that matters: the held-out split is **patient-level**, not segment-level — there is no leakage between train and test, so the held-out metric reflects performance on patients the model has never heard. **85% crackle detection** on that held-out cohort. The training notebook (`notebooks/06_unsloth_binary_phase1.ipynb`) is in the public repository and re-runs end-to-end on a Kaggle T4 GPU. The merged adapter (this model) loads via a single line in any inference notebook. The same model runs a second pass after classification to produce the AI Clinical Note. Hackathon-grade, not FDA-cleared — explicitly so. The repository's `REASONS_WE_WILL_FAIL.md` documents this and every other honest limit. This is the specific, impactful clinical task Unsloth made shippable.

---

### Link 4 · Full storytelling film · 12 minutes · must-watch

**URL:** https://youtu.be/2p932LTc_wE

**Description** *(≈200 words):*

> The full storytelling arc behind the submission. The 3-minute Kaggle cut in the media gallery is the pitch; this 12-minute film is the *why*. It opens with ten seconds of a child with pneumonia breathing, then the data: 4.9 million children under five lost in 2024, 1.17 million from pneumonia and diarrhea alone, one child every 39 seconds (UNICEF, 2019). The peer-reviewed Umlazi case-series (Nsibande et al., 2013) — five infants who died on the way home from hospital — is dramatized as one young mother on a bus, told as a film, then told again with Malaika in her bag. The middle is the engineering case — why only Gemma 4 E2B meets the four constraints, what the agentic skills do, why the WHO IMCI classification is hard-coded code and not LLM output. The closing argument is on open source: the AI that decides whether a child lives must not belong to one company. We don't know which of those 4.9 million children would have been the next Sundar Pichai, Wangari Maathai, or Yusuf Hamied. Every claim is cited; the citation list is in `SOURCES.md` in the repository.

---

### Link 5 · Full app demo · Samsung A53

**URL:** https://youtu.be/yV8jBH6-_I0

**Description** *(≈200 words):*

> The Tier-0 phone proof. An unedited screen-and-hands walkthrough of the Flutter app running Gemma 4 E2B on a real **$60 Samsung A53** with a Mali-G68 GPU — the kind of phone the village mother in our story actually owns. Airplane mode is toggled on at the start of the video and stays on; no SIM, no Wi-Fi, no cloud — every inference is on the device. The video walks through a complete IMCI encounter: voice-driven Q&A in the caregiver's language (offline STT + TTS on Android-native CPU engines), in-app camera capture for the child's photo, on-device vision analysis for alertness / sunken eyes / visible ribs / edema, Q&A vs vision reconciliation that flags contradictions, the deterministic WHO IMCI classification reveal (severe pneumonia / pneumonia / no pneumonia, by hard-coded thresholds — *never* LLM output), and the treatment plan rendered in the caregiver's language with read-aloud instructions. No cuts, no edits. What you see is what runs. The point of this video is to make the on-device claim impossible to dismiss as "demo magic" — it is a real phone, a real model, a real assessment.

---

### Link 6 · Sources & citations · SOURCES.md

**URL:** https://github.com/Vimalk0703/Google-Gemma4-good-hackathon-VimalXMark/blob/main/SOURCES.md

**Description** *(≈200 words):*

> The receipts. A single document with the primary-source URL for every numerical and clinical claim in the videos, the writeup, and the landing page. UNICEF / WHO / World Bank / UN-DESA *Levels & Trends in Child Mortality* for the 4.9M and the 58%-in-Sub-Saharan-Africa numbers; WHO Guideline 2024 for the 1.17M pneumonia + diarrhea deaths; the UNICEF 2019 press release for the "39 seconds" cadence (with an explicit note that this number was derived from 2018 data and we say so); the Cochrane systematic review (Gera et al., 2016) for the 15% IMCI mortality reduction; the BMC/Africa Health Sciences Nsibande et al. 2013 case-series for the Umlazi story; Källander et al. *Bulletin of the WHO* 2008 for the two-day rural-Uganda care-seeking delay; the WHO Africa BMJ Glob Health 2024 modelling study for the 6.1M projected 2030 health-worker shortage; GSMA *Mobile Economy Sub-Saharan Africa* for the 489M subscribers; the ICBHI 2017 challenge paper for the respiratory dataset; Google's Gemma 4 model card for the per-layer-embedding architecture. Every link is live-verified. Fact-check any claim in under a minute.

---

### Link 7 · Anti-marketing · REASONS_WE_WILL_FAIL.md

**URL:** https://github.com/Vimalk0703/Google-Gemma4-good-hackathon-VimalXMark/blob/main/REASONS_WE_WILL_FAIL.md

**Description** *(≈200 words):*

> The list of things Malaika deliberately does *not* claim — written before the video was shot, kept on the record. Camera + model cannot share VRAM on the Samsung A53's Mali-G68 GPU, so our phone story is built around solving that constraint, not pretending it does not exist. We do not claim breathing-rate estimation from video, real-time continuous monitoring, FDA clearance, or clinical-trial outcomes; the system is decision support for trained health workers operating under the WHO IMCI protocol, never a standalone diagnostic device. The ICBHI 2017 training set is predominantly Western patients, so our breath-sound fine-tune carries the population-bias of the dataset and we acknowledge it. The 175,000-children-a-year impact number is explicitly a **projection from the Cochrane 15% IMCI mortality reduction**, applied to pneumonia + diarrhea deaths — it is *not* a measured outcome of Malaika in the field, and the writeup, landing page, and video all say "projection, not measurement" wherever this number appears. We came with receipts for what works; this document is the receipts for what doesn't. Anti-marketing is the discipline that makes the rest of the claims trustworthy.

---

## 7. Project Description  *(form field — max 1,500 words)*

The full paste-ready body lives in its own file — **[`KAGGLE_PROJECT_DESCRIPTION.md`](KAGGLE_PROJECT_DESCRIPTION.md)** — formatted for maximum readability inside Kaggle's textbox. **1,359 words** (comfortably under the 1,500-word limit). Markdown is supported by Kaggle Writeups, so the headings, blockquotes, and emphasis all render.

To submit:

1. Open [`KAGGLE_PROJECT_DESCRIPTION.md`](KAGGLE_PROJECT_DESCRIPTION.md) on GitHub and click **Raw** (top-right of the file view) to get the unrendered markdown.
2. Copy from the first heading (`# Malaika — putting the WHO's…`) through the final signature line (`— *Vimal & Mark, May 2026. Apache 2.0.*`).
3. Paste into the Kaggle Writeup *Project Description* textbox.

Kept as a separate file so it is also the single source of truth — any edits there ship straight into the form without re-syncing this writeup.

---

## 8. Pre-submit checklist

Before clicking **Submit** on Kaggle:

- [ ] Title (≤80 chars) pasted
- [ ] Subtitle (≤140 chars) pasted
- [ ] Track set to **Health & Sciences**
- [ ] Card thumbnail (560×280) uploaded
- [ ] Short submission video (≤ 3:00) attached to media gallery — **VERIFY DURATION FIRST**
- [ ] Long film (12 min) attached to media gallery
- [ ] App demo video attached to media gallery
- [ ] Project Description (body of §7 above) pasted into textbox
- [ ] Word count verified ≤ 1,500
- [ ] Project Links all added (live demo, GitHub repo, APK, HF model, sources, REASONS_WE_WILL_FAIL)
- [ ] GitHub repo set to **public**
- [ ] Vercel deployment is live and the landing page loads with no login
- [ ] Apache 2.0 LICENSE file is in the repo root
