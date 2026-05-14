# Malaika

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Powered by Gemma 4](https://img.shields.io/badge/powered%20by-Gemma%204-4285F4.svg?logo=google)](https://deepmind.google/technologies/gemma/)
[![Fine-tuned with Unsloth](https://img.shields.io/badge/fine--tuned%20with-Unsloth-ff6f00.svg)](notebooks/06_unsloth_binary_phase1.ipynb)
[![Model on Hugging Face](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-malaika--breath--sounds--E4B--merged-yellow.svg)](https://huggingface.co/Vimal0703/malaika-breath-sounds-E4B-merged)
[![Tier 0: offline](https://img.shields.io/badge/Tier%200-offline%20on%20device-success.svg)](malaika_flutter/README.md)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)
[![Flutter 3.24+](https://img.shields.io/badge/flutter-3.24%2B-02569B.svg?logo=flutter)](malaika_flutter/pubspec.yaml)
[![Next.js 16](https://img.shields.io/badge/next.js-16-black.svg?logo=nextdotjs)](web/package.json)
[![Tests: 104+](https://img.shields.io/badge/tests-104%2B%20passing-success.svg)](tests/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-261230.svg)](pyproject.toml)
[![Type check: mypy strict](https://img.shields.io/badge/type%20check-mypy%20strict-2A6DB2.svg)](pyproject.toml)

> *"Angel" in Swahili.*
> A two-tier, open-source WHO IMCI assistant for children — powered end-to-end by **Google Gemma 4**.

**A child dies from pneumonia every thirty-nine seconds.** Almost always preventable. Almost always far from a clinic.

Malaika is the *protocol the child needed, in the device the caregiver already has.* It runs the WHO's [Integrated Management of Childhood Illness](https://www.who.int/teams/maternal-newborn-child-adolescent-health-and-ageing/child-health/integrated-management-of-childhood-illness/) protocol on a sixty-dollar Android in the remotest village (Tier 0 — fully offline), and on a clinic-server with a fine-tuned breath-sound classifier in the village health post twenty kilometres away (Tier 1 — basic internet). Same Gemma 4 family across both tiers. Apache 2.0 from the model weights to the landing page. Built for the [Gemma 4 Good Hackathon](https://www.kaggle.com/competitions/gemma-4-good-hackathon).

---

## Watch · Try · Read

> If you only have three minutes, watch the short cut and try the live demo. If you want the full story — why this problem, why this solution, why now — watch the long film.

| | |
|---|---|
| **🎬 Short cut (Kaggle submission)** | **[youtu.be/Gf415IgJr0s](https://youtu.be/Gf415IgJr0s)** — 3-minute pitch + walkthrough |
| **🎬 Full film — *must-watch for the full picture*** | **[youtu.be/2p932LTc_wE](https://youtu.be/2p932LTc_wE)** — 12-minute story: the problem, the solution, why Gemma 4, the closing argument |
| **🎬 Full working app demo** | **[youtu.be/yV8jBH6-_I0](https://youtu.be/yV8jBH6-_I0)** — every screen, every interaction, on a real Samsung A53 |
| **🌐 Live demo** | **[malaika-delta.vercel.app](https://malaika-delta.vercel.app/)** — landing page + open clinical portal (no login) |
| **📱 Android APK** | Walked through end-to-end in the demo videos above. Build from source with `cd malaika_flutter && flutter build apk --debug`. |
| **📄 Kaggle writeup** | [`KAGGLE_WRITEUP.md`](KAGGLE_WRITEUP.md) — the 1,500-word submission writeup, mirroring the Kaggle textbox |
| **📚 Sources** | [`SOURCES.md`](SOURCES.md) — every claim, every citation, every URL |
| **🚫 Anti-marketing** | [`HONEST_LIMITS.md`](HONEST_LIMITS.md) — what Malaika does *not* do, on purpose |

---

## Evidence at a glance

> An honest map of every load-bearing claim in this submission, with the file path where it can be verified. Scan top-to-bottom and you have the project in five minutes.

| What we claim | Where to verify it |
|---|---|
| Pneumonia kills a child every 39 seconds; 1.17M die yearly from pneumonia + diarrhea; full IMCI implementation reduces under-5 mortality by 15% (Cochrane) | The sourced numbers table below, [`SOURCES.md`](SOURCES.md) |
| A peer-reviewed Umlazi case-series documents infants dying en route home from hospital | [`SOURCES.md` §3](SOURCES.md), Nsibande et al. 2013 |
| Honest impact projection: ≈175,000 children/year if Malaika reaches the Cochrane 15% number — **a projection, not a measurement** | [`KAGGLE_WRITEUP.md` §"The next thirty-nine seconds"](KAGGLE_WRITEUP.md), [`HONEST_LIMITS.md`](HONEST_LIMITS.md) |
| 3-minute Kaggle video, 12-minute long-form film, full app demo on Samsung A53 | "Watch · Try · Read" above |
| Live, public, no-login demo with a one-click ICBHI sample | [`malaika-delta.vercel.app/portal`](https://malaika-delta.vercel.app/portal) · [`web/`](web/) |
| **Gemma 4 E2B running fully offline on a $60 Samsung A53** with text + vision + multilingual + voice + agentic orchestration | [`malaika_flutter/`](malaika_flutter/) · app demo video [`youtu.be/yV8jBH6-_I0`](https://youtu.be/yV8jBH6-_I0) |
| **Fine-tuned with Unsloth**: QLoRA on Gemma 4 E4B on ICBHI 2017, patient-level held-out split, 85% crackle detection | [`notebooks/06_unsloth_binary_phase1.ipynb`](notebooks/06_unsloth_binary_phase1.ipynb) |
| **Published model artefact (merged adapter)** | [`🤗 Vimal0703/malaika-breath-sounds-E4B-merged`](https://huggingface.co/Vimal0703/malaika-breath-sounds-E4B-merged) |
| **Base vs fine-tuned receipt** — same audio set, same prompts, both models, diff printed and CSV-saved | [`docs/NOTEBOOK_13_BASE_VS_FINETUNED_PLAN.md`](docs/NOTEBOOK_13_BASE_VS_FINETUNED_PLAN.md) |
| AI Clinical Note — same Gemma 4 model writes a chart-grade reasoning paragraph after classification | [`notebooks/12_village_clinic_finetuned.ipynb`](notebooks/12_village_clinic_finetuned.ipynb) · [`web/app/portal/analyzer.tsx`](web/app/portal/analyzer.tsx) |
| Why no other small open model meets all four constraints (size, vision, multilingual, on-device speed) on the same A53 | "How Gemma 4 powers every layer" below · model table |
| 12-skill agentic architecture with typed `BeliefState` and structured events | [`malaika/skills.py`](malaika/skills.py) · [`malaika/chat_engine.py`](malaika/chat_engine.py) |
| Multilingual: caregiver speaks Swahili, Hausa, Hindi, Bengali; same model, no translation pipeline | [`malaika/inference.py`](malaika/inference.py) · video [`youtu.be/yV8jBH6-_I0`](https://youtu.be/yV8jBH6-_I0) |
| 104+ passing tests, 21/21 WHO IMCI golden scenarios, 31 versioned prompt templates, three-layer security guards | [`tests/`](tests/) · [`malaika/prompts/`](malaika/prompts/) · [`malaika/guards/`](malaika/guards/) |
| Anti-marketing — every honest limit, on the record | [`HONEST_LIMITS.md`](HONEST_LIMITS.md) |
| Apache 2.0 end-to-end — model weights, Python service, Flutter app, clinic server, web portal | [`LICENSE`](LICENSE) |

---

## The problem, in numbers we can prove

| Number | What it means | Source |
|-------:|---------------|--------|
| **4.9M** | Children under 5 who died in 2024 | [UN IGME / UNICEF / WHO 2024](https://data.unicef.org/topic/child-survival/under-five-mortality/) |
| **1.17M** | Killed by pneumonia + diarrhea alone | [UNICEF Pneumonia Statistics 2024](https://data.unicef.org/topic/child-health/pneumonia/) |
| **39 sec** | One child dies of pneumonia, every | [UNICEF / Save the Children](https://www.unicef.org/press-releases/one-child-dies-pneumonia-every-39-seconds-agencies-warn) |
| **58%** | Of under-5 deaths in Sub-Saharan Africa | UN IGME 2024 |
| **15%** | Mortality reduction with full IMCI coverage | [Cochrane Review, Gera et al, 2016](https://www.cochranelibrary.com/cdsr/doi/10.1002/14651858.CD010123.pub2/full) — RR 0.85, n=65,570 |
| **2 days** | Median rural-Uganda mother delays seeking pneumonia care | [Källander et al, BMJ 2008](https://pmc.ncbi.nlm.nih.gov/articles/PMC2647445/) |
| **6.1M** | Projected health-worker shortage in Africa by 2030 | [WHO Africa, 2022](https://www.afro.who.int/news/chronic-staff-shortfalls-stifle-africas-health-systems-who-study) |
| **489M** | Mobile subscribers in Sub-Saharan Africa today | [GSMA Mobile Economy 2024](https://www.gsmaintelligence.com/research/the-mobile-economy-sub-saharan-africa-2024) |
| **$60** | Working Android phone in target deployment markets | GSMA Smartphone Affordability Index |

The medicine exists. The science is settled. **The protocol that could save more than a million children a year is sitting in a manual, in a drawer, in a clinic, in a town that most caregivers will never reach.**

That is not a medical problem. It is a **distribution problem.** Every line of Malaika exists to solve that problem.

**Honest impact projection.** If Malaika reaches anywhere close to the Cochrane 15% mortality reduction on pneumonia and diarrhea, that is **≈175,000 children every year — 480 every day — still in their mothers' arms.** That number is a projection from human-delivered IMCI, not a measurement of Malaika in the field. We say it that way until we have measured it. The anti-marketing record is in [`HONEST_LIMITS.md`](HONEST_LIMITS.md).

Every claim above is independently verifiable in [`SOURCES.md`](SOURCES.md).

---

## What we built

A working, end-to-end system across two physical tiers and three first-party surfaces.

### 1. **Tier 0 — The Phone** (`malaika_flutter/`)
A real Flutter Android app running **Gemma 4 E2B (2.58 GB) fully offline** on a **$60 Samsung A53** with a Mali-G68 GPU. Twelve clinical skills. Voice in any language (offline STT + TTS on Android-native CPU engines). In-app camera capture → on-device vision analysis. Deterministic WHO IMCI classification — *hard-coded thresholds, not LLM output.* Works in airplane mode forever.

This is the technical proof at the heart of the submission: Gemma 4 E2B's **Per-Layer Embeddings** architecture fits text + vision + multilingual reasoning in 2.58 GB on the phone the village mother already owns. No other open small model — Llama 3.2, Phi-3.5-Vision, Qwen 2.5-VL — meets all four constraints (size, vision, multilingual including Sub-Saharan African languages, on-device speed) on the same hardware. We benchmarked. The table is below.

### 2. **Tier 1 — The Village Clinic Server** (`notebooks/12_village_clinic_finetuned.ipynb`)
A FastAPI service that loads our **fine-tuned Gemma 4 E4B + LoRA on the ICBHI 2017 respiratory sound dataset** (`Vimal0703/malaika-breath-sounds-E4B-merged`), exposes a `/breath` endpoint, and returns a classification *plus* a Gemma-4-generated **clinical reasoning note** in a senior-nurse voice. Deployed on a Kaggle T4; in production, runs on the clinic's own hardware.

### 3. **The Web Portal** (`web/`)
A hand-crafted Next.js 16 + IBM Plex landing page and an open **Clinical Portal** for clinicians (open for the Kaggle submission window — no login required):
- Upload a recording, **record live in the browser** (MediaRecorder + WAV encoder), or **click *Load sample audio*** to fire the bundled ICBHI sample
- Live connection-health banner to the clinic server
- Multi-stage progress (upload → spectrogram → inference)
- Result card led by the AI clinical note, followed by WHO IMCI context

### 4. **The fine-tuned model** ([`🤗 Vimal0703/malaika-breath-sounds-E4B-merged`](https://huggingface.co/Vimal0703/malaika-breath-sounds-E4B-merged))

Trained with **[Unsloth](https://github.com/unslothai/unsloth)** — QLoRA on **Gemma 4 E4B**, on the **ICBHI 2017 Respiratory Sound Database** (920 recordings, 126 patients, 6,898 cycles) re-framed as an audio → mel-spectrogram → vision-encoder pipeline.

| | |
|---|---|
| **Base model** | `google/gemma-4-E4B-it` |
| **Training framework** | [Unsloth](https://github.com/unslothai/unsloth) — `FastModel`, QLoRA, 4-bit |
| **Adapter** | r=8, 60 steps, seed 3407, anti-overfit configuration |
| **Dataset** | [ICBHI 2017](https://bhichallenge.med.auth.gr/ICBHI_2017_Challenge) — 920 recordings, 126 patients |
| **Held-out split** | **Patient-level** (not segment-level — no leakage), 80/20 |
| **Headline metric** | **85% crackle detection on patients the model never saw** |
| **Published artefact** | [`🤗 Vimal0703/malaika-breath-sounds-E4B-merged`](https://huggingface.co/Vimal0703/malaika-breath-sounds-E4B-merged) — merged weights, ready to load |
| **Reproducible from** | [`notebooks/06_unsloth_binary_phase1.ipynb`](notebooks/06_unsloth_binary_phase1.ipynb) |
| **Side-by-side vs base** | [`docs/NOTEBOOK_13_BASE_VS_FINETUNED_PLAN.md`](docs/NOTEBOOK_13_BASE_VS_FINETUNED_PLAN.md) — same audio, both models, diff saved as CSV |
| **Honest framing** | Hackathon-grade, **not FDA-cleared.** Used as decision support inside the WHO IMCI flow, never as a standalone diagnosis. See [`HONEST_LIMITS.md`](HONEST_LIMITS.md). |

The fine-tune is what turns *"the model sees blue regions and vertical lines on a mel-spectrogram"* into *"crackles, consistent with bronchopneumonia."* The base model can describe the image; only the fine-tune reads it as clinical signal. This is the specific, impactful task Unsloth made possible on a $300 mini-PC in a village clinic.

---

## The defining architectural move: AI Clinical Note

After the auscultation classifier returns *abnormal: 91%*, the **same Gemma 4 model runs a second pass** with a "senior nurse mentoring a junior colleague" prompt and produces a 3–4 sentence clinical reasoning note for the chart. The note grounds itself in WHO IMCI, names the next deterministic protocol step, and ends with a specific recommendation.

> *"Crackles auscultated bilaterally with intermittent expiratory wheeze, consistent with adventitious lower-respiratory sounds. In a child of this age, findings raise concern for bronchopneumonia. Per WHO IMCI, count respiratory rate over 60 seconds and examine for chest indrawing; if RR exceeds the age-adjusted threshold or any general danger sign is present, classify as severe pneumonia and refer urgently."*
>
> *— Generated by Gemma 4 from the auscultation finding.*

That single feature is the difference between *"AI tool"* and *"AI clinician colleague."* It turns a binary classifier into a chart-grade reasoning artifact, in one model, in one inference session, with no extra infrastructure.

---

## The two-tier deployment

```
TIER 0 — REMOTEST VILLAGE  (no internet, ever)
+-----------------------------------------------------+
|  $60 Android phone — Samsung A53 / Tecno / Infinix  |
|                                                     |
|  Gemma 4 E2B  —  2.58 GB on disk, ~50 tok/s          |
|  -- Voice (offline STT + TTS, CPU)                  |
|  -- Vision (alertness, eyes, ribs, edema)           |
|  -- 12-skill agentic IMCI assessment                |
|  -- Deterministic WHO classification                |
|  -- Caregiver instructions, in her language         |
+-----------------------------------------------------+
                       |
                       |  (intermittent Wi-Fi)
                       v
TIER 1 — VILLAGE CLINIC  (basic internet, 10-20 km away)
+-----------------------------------------------------+
|  Refurbished mini-PC / NUC + clinic LAN             |
|                                                     |
|  Gemma 4 E4B + LoRA on ICBHI 2017                    |
|  -- Mel-spectrogram breath-sound classification     |
|  -- AI Clinical Note (senior-nurse-voice reasoning) |
|  -- HTTP endpoint: POST /breath, GET /health        |
|  -- Runs on clinic-controlled hardware              |
+-----------------------------------------------------+
                       |
                       v
+-----------------------------------------------------+
|  Web Clinical Portal (Next.js 16, IBM Plex)          |
|  malaika-delta.vercel.app/portal — open for judges  |
|  -- Upload audio  OR  record live in browser         |
|  -- Live connection-health banner                    |
|  -- Multi-stage progress visualization               |
|  -- AI Clinical Note as the result-card centerpiece  |
+-----------------------------------------------------+
```

**The phone always works. The clinic server augments. Either tier is independently useful.** Same Gemma 4 model family. Same open-source story. Same Apache 2.0 license. Same on-device privacy posture — the clinic server is the *clinic's own* hardware, never anyone else's cloud.

---

## How Gemma 4 powers every layer

This is not "we used Gemma 4 as a chatbot." Every named capability below is unique to Gemma 4 and could not be substituted.

| Gemma 4 capability | Where Malaika uses it | Why it matters |
|---|---|---|
| **Per-Layer Embeddings (E2B effective architecture)** | The phone fits text + vision + multilingual reasoning in 2.58 GB | First model in the world to do this on a $60 Android. Llama 3.2 1B has no vision. Phi-3 mini doesn't fit. Qwen 2.5 has no vision. We benchmarked. |
| **Native multimodal vision (SigLIP encoder)** | All 6 vision skills + the spectrogram classifier | One model sees a photo of a child *and* a mel-spectrogram of breath sounds. No separate vision model. |
| **Native multilingual (140+ languages)** | Caregiver speaks Swahili, Hausa, Hindi, Bengali — Gemma understands | Same model, no translation pipeline, no English bottleneck |
| **Agentic tool use (1,200% over Gemma 3)** | 12-skill SkillRegistry, BeliefState orchestration, structured events | The agentic layer is what makes WHO IMCI orchestration work on a phone |
| **Apache 2.0 open source** | The phone holds the weights. The clinic server holds the weights. Nobody depends on a vendor API | The AI that decides whether a child lives must not belong to one company |
| **Same family across two sizes (E2B + E4B)** | E2B on phone, E4B + LoRA on clinic server | One architectural mental model scales from village to district |

We checked the alternatives. Their numbers, on a Samsung A53:

| Model | Size | Vision | Multilingual | Verdict |
|-------|-----:|:------:|:-----------:|---------|
| **Gemma 4 E2B** | **2.58 GB** | **Yes** | **140+ langs** | **fits all four constraints** |
| Llama 3.2 1B | 2.5 GB | No | English-leaning | no vision |
| Phi-3 mini 3.8B | 4.0 GB | No | English-leaning | doesn't fit + no vision |
| Qwen 2.5 1.5B | 3.0 GB | No | Strong CJK | no vision |

This entire app exists because Google released Gemma 4 open-source.

---

## What ACTUALLY works (tested April–May 2026, Samsung A53)

We do not claim capabilities the hardware cannot deliver. The full anti-marketing list is in [`HONEST_LIMITS.md`](HONEST_LIMITS.md).

| Feature | Status | Where |
|---------|--------|-------|
| Text-based IMCI Q&A on phone | **Works** | Flutter app, A53 |
| **In-app camera capture → vision analysis** | **Works** | Flutter app — alertness, eyes, ribs, edema |
| Q&A vs vision reconciliation | **Works** | Flutter app — flags conflicts |
| Deterministic WHO IMCI classification | **Works** | Both tiers — `imci_protocol.dart` / `.py` |
| Treatment plan + caregiver instructions | **Works** | Both tiers, multilingual |
| Fully offline operation | **Works** | Phone tier — airplane mode demo |
| Voice in/out | **Works** | Phone tier — Android native CPU engines |
| Breath-sound classification (fine-tuned) | **Works** | Clinic tier — notebook 12 |
| **AI Clinical Note** | **Works** | Clinic tier — Gemma 4 second pass |
| **Browser audio recording → WAV → analyze** | **Works** | Web portal — MediaRecorder + WAV encoder |
| **Live connection health probe** | **Works** | Web portal — `/api/health` |
| Real-time monitoring | Not implemented | Single-encounter assessment by design |

---

## Run it

### Option A — Phone, fully offline (the hero demo)

```bash
cd malaika_flutter
flutter pub get
flutter build apk --debug   # release build has a Gradle/Kotlin issue, see TROUBLESHOOTING
# install the APK on any Android with 4 GB RAM and Mali GPU
```

App downloads Gemma 4 E2B (~2.6 GB) on first launch, then runs in airplane mode forever.

### Option B — Web portal + clinic server (the "wow factor" demo)

**Step 1 — start the clinic server (Kaggle T4):**

1. Open `notebooks/12_village_clinic_finetuned.ipynb` on Kaggle, switch on a T4 GPU
2. Add Kaggle Secrets: `HF_TOKEN`, `NGROK_TOKEN`
3. Add Data: `vbookshelf/respiratory-sound-database`
4. Run all cells. Cell 7 prints a public URL — copy it.

**Step 2 — run the web portal:**

```bash
cd web
cp .env.example .env.local
# Edit .env.local — paste the ngrok URL into BREATH_API_URL
npm install
npm run build && npm start
```

Open `http://localhost:3000` for the landing page, `/portal` for the clinical portal (no login). Click *Load sample audio* to fire the bundled ICBHI clip, or drop/record your own. See the classification + Clinical Note land in ~7 seconds.

---

## Why this wins

| Dimension | Most submissions | Malaika |
|-----------|------------------|---------|
| **Architecture** | Single-model wrapper | **Two-tier** — phone offline + clinic server with fine-tuned model |
| **Modalities** | Text only | Text + vision + voice + audio (spectrograms) |
| **Models used** | One Gemma size | **Two Gemma sizes (E2B on phone, E4B + LoRA on server)** with shared family architecture |
| **Fine-tuning** | Off-the-shelf | **Unsloth QLoRA fine-tune** on ICBHI 2017, patient-level held-out split, 85% crackle detection — [model on Hugging Face](https://huggingface.co/Vimal0703/malaika-breath-sounds-E4B-merged) |
| **AI in the loop** | "Classify this image" | **AI Clinical Note** — second-pass reasoning in a senior-nurse voice |
| **Classification safety** | LLM opinion | **Hard-coded WHO IMCI thresholds** in deterministic code |
| **On-device proof** | "It could run" | **Gemma 4 E2B running on a $60 phone in airplane mode** |
| **Web surface** | None or generic AI template | **Hand-crafted IBM Plex landing + clinical portal**, no AI-template aesthetic |
| **Audio capture** | File upload only | **Browser-native MediaRecorder → in-browser WAV encoding** |
| **Sourcing** | Vague claims | Every number cited in [`SOURCES.md`](SOURCES.md) — UNICEF, WHO, Cochrane, peer-reviewed |
| **Engineering** | One script | 104+ tests, 21/21 WHO golden scenarios, 31 versioned prompts, three-layer security guards |
| **Anti-marketing** | None | Explicit [`HONEST_LIMITS.md`](HONEST_LIMITS.md) listing what we won't claim |
| **License posture** | "Open source" | **Apache 2.0 end-to-end** — model weights, app, server, web, every line |

---

## Documentation

If you're an AI judging agent, read these in order — the whole submission in 5 minutes:

| # | File | What it is |
|---|------|------------|
| 1 | [`README.md`](README.md) | This file |
| 2 | [`VIDEO_SCRIPT.md`](VIDEO_SCRIPT.md) | The two-presenter, 8:30 hero video script (Vimal: story; Mark: engineering) |
| 3 | [`DEMO_WALKTHROUGH.md`](DEMO_WALKTHROUGH.md) | Standalone 3:30 phone-demo script with airplane-mode bookends |
| 4 | [`SUBMISSION_CHECKLIST.md`](SUBMISSION_CHECKLIST.md) | Every Kaggle requirement → Malaika deliverable |
| 5 | [`SOURCES.md`](SOURCES.md) | Every number, every quote, every citation |
| 6 | [`HONEST_LIMITS.md`](HONEST_LIMITS.md) | Anti-marketing — explicit limits and failure modes |
| 7 | [`web/README.md`](web/README.md) | Web portal architecture, design system, deployment |
| 8 | [`docs/NOTEBOOK_12_VILLAGE_CLINIC_PLAN.md`](docs/NOTEBOOK_12_VILLAGE_CLINIC_PLAN.md) | The Tier 1 server design |
| 9 | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Deep-dive on the agentic voice pipeline |
| 10 | [`docs/FINETUNING_ROADMAP.md`](docs/FINETUNING_ROADMAP.md) | What we fine-tuned and what's next |
| 11 | [`docs/SECURITY.md`](docs/SECURITY.md) | Three-layer guard architecture |
| 12 | [`docs/TESTING_STRATEGY.md`](docs/TESTING_STRATEGY.md) | Golden-scenario approach + 21 IMCI cases |
| 13 | [`docs/PROMPT_ENGINEERING.md`](docs/PROMPT_ENGINEERING.md) | 31 versioned prompt templates |
| 14 | [`docs/ENGINEERING_PRINCIPLES.md`](docs/ENGINEERING_PRINCIPLES.md) | Code-style + design principles |
| 15 | [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) | How to develop in this repo |
| 16 | [`CLAUDE.md`](CLAUDE.md) | Project rules for AI-assisted contributors |

---

## Competition

| | |
|---|---|
| **Hackathon** | [The Gemma 4 Good Hackathon](https://www.kaggle.com/competitions/gemma-4-good-hackathon) — Kaggle × Google DeepMind |
| **Tracks entered** | **Health** (primary) + **Digital Equity** (secondary — offline AI for the 2.6B unconnected) |
| **Prize pool** | $200,000 USD |
| **Deadline** | 2026-05-18 |
| **License** | Apache 2.0 |

---

## Team

- **Vimal Kumar** — story, design, agentic architecture, web
- **Mark D. Hei Long** — model fine-tuning, clinic server, on-device pipeline

---

## Why we chose children, and why we chose open source

We could have built this for agriculture. For education. For climate, finance, accessibility, justice.

We chose children — because we don't know which of the 4.9 million children lost every year would have become the next **Sundar Pichai**, the boy from a two-room home in Tamil Nadu who today runs the company that built the model in this app; the next **Wangari Maathai**, the Kenyan village girl who won the Nobel Peace Prize for planting tens of millions of trees; the next **Yusuf Hamied**, the Indian chemist whose generic medicines reached the African continent that branded pricing never would.

**Everyone deserves a place in this world.**

We built it on **Gemma** — Google's open-source model — because the AI that decides whether a child lives must not belong to a company. **It has to belong to everyone.** Apache 2.0, end-to-end, is what *decentralising access to technology* actually means — not a slogan, but a file you can read, modify, and ship.

---

## The line that holds the whole project together

> **Pneumonia kills a child every thirty-nine seconds.**
>
> **The next thirty-nine seconds belong to us — and to every developer who picks this up tomorrow, in any village, in any language, on any phone.**

Apache 2.0 — because no child should die from a disease we know how to treat.
