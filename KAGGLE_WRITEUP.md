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

Each row below maps to one Kaggle *Project Link* entry. Add them in this order — the first three are the load-bearing artefacts a judge should touch first. If the form accepts a description per link, paste the *Description* column. If it only accepts label + URL, fold the description into the label.

| Label | URL | Description |
|---|---|---|
| **Live demo · open clinical portal** | https://malaika-delta.vercel.app/ | The Tier-1 clinical portal — open, no login. Click *Load sample audio* to fire the bundled ICBHI 2017 clip and see the full pipeline (mel-spectrogram → fine-tuned Gemma 4 classification → AI Clinical Note) in ~7 seconds. The cleanest five-minute proof of the submission. |
| **Public code repository · GitHub** | https://github.com/Vimalk0703/Google-Gemma4-good-hackathon-VimalXMark | Apache 2.0 end-to-end — Flutter app, Python service, fine-tuning notebooks, clinic server, web portal. Start with `README.md` → "Evidence at a glance" for the verification trail. |
| **Fine-tuned model · Hugging Face** | https://huggingface.co/Vimal0703/malaika-breath-sounds-E4B-merged | The Unsloth award submission. Merged Gemma 4 E4B + QLoRA adapter, fine-tuned on ICBHI 2017 with a patient-level held-out split (no segment-level leakage). 85% crackle detection on patients the model never saw. Reproducible from `notebooks/06_unsloth_binary_phase1.ipynb`. |
| **Full storytelling film · 12 min · must-watch** | https://youtu.be/2p932LTc_wE | Long-form video for the full picture: the problem, the Umlazi mother, why pneumonia, why only Gemma 4 fits the constraints, the closing argument. Every claim cited; pairs with `SOURCES.md`. |
| **Full app demo · Samsung A53** | https://youtu.be/yV8jBH6-_I0 | Unedited walkthrough of the Flutter app on a real $60 Samsung A53 in airplane mode — Gemma 4 E2B running fully offline. Every screen, every interaction, no cuts. |
| **Sources & citations · SOURCES.md** | https://github.com/Vimalk0703/Google-Gemma4-good-hackathon-VimalXMark/blob/main/SOURCES.md | Primary-source URL for every numerical and clinical claim in the videos and the writeup — UNICEF, WHO, the Cochrane Review, peer-reviewed journals, and the original ICBHI 2017 paper. |
| **Anti-marketing · REASONS_WE_WILL_FAIL.md** | https://github.com/Vimalk0703/Google-Gemma4-good-hackathon-VimalXMark/blob/main/REASONS_WE_WILL_FAIL.md | The list of capabilities Malaika deliberately does *not* claim — phone GPU constraints, hackathon-grade vs FDA-cleared, single-encounter (not real-time), and the honest "projection, not measurement" caveat on the 175,000-children/year impact line. |

---

## 7. Project Description  *(form field — max 1,500 words)*

> *Everything below this line is the body of the Kaggle Writeup. Copy from "Malaika — putting…" through the closing line. Markdown is supported by Kaggle Writeups.*

---

# Malaika — putting the WHO's child-survival protocol in a sixty-dollar phone

> **A child dies of pneumonia every thirty-nine seconds.** The medicine costs five cents. The protocol is thirty years old. *It still isn't reaching her.* Malaika puts it in her hand.

*👉 If you have twelve minutes, please watch the [full storytelling film](https://youtu.be/2p932LTc_wE) — it is a must for the full picture. The [3-minute pitch](https://youtu.be/Gf415IgJr0s) is in the media gallery.*

## The problem isn't medicine. It's distribution.

In 2024, **4.9 million children** under five did not see their fifth birthday (UN IGME / UNICEF / WHO, 2025). Fifty-eight percent in Sub-Saharan Africa. Of those, **1.17 million** were killed by two diseases — pneumonia and diarrhea (WHO Guideline, 2024).

The numbers persist not because the medicine fails, but because the medicine never arrives. The WHO wrote a protocol for these conditions — **Integrated Management of Childhood Illness (IMCI)** — in the mid-1990s. A Cochrane review (Gera et al., 2016) found that fully implemented IMCI cuts under-five mortality by **15%**.

But to learn IMCI a nurse trains for eleven days. Africa has **1.5 health workers** per thousand people; the WHO minimum is 4.45. By 2030 the shortage will exceed **6 million** (WHO Africa, 2024). The median rural-Uganda mother waits **two days** before seeking pneumonia care (Källander et al., Bull WHO, 2008). For pneumonia, two days is the entire window between life and death.

The protocol that could save a million children a year is sitting in a manual, in a drawer, in a clinic she will never reach. That is not a medical problem. **It is a distribution problem.**

## Umlazi

A peer-reviewed case-series from a township outside Durban (Nsibande et al., 2013) documents **five infants who died en route home from hospital**. A young mother is discharged with her newborn. Halfway home on the bus, the baby starts breathing too fast. She knows something is wrong. What she doesn't know is *how* wrong — whether tonight is *get off this bus* or *see how he sleeps*.

That second kind of knowing has a name: **the WHO IMCI protocol**. That night, it was sitting in a manual, in a drawer, in a clinic she couldn't afford to ride to. She has no bus fare. She holds her child. She prays. By the time she steps off, the baby has died.

What was missing was never only the medicine. It was the **certainty** of knowing what tonight is — the certainty to beg the driver, wake a neighbour, walk the road. *It is everything she did not have.*

## The paradox

**The phone got to the village before the doctor did.** **489 million** unique mobile subscribers in Sub-Saharan Africa (GSMA, 2023). Entry-level Android handsets at **~$60**. The hardware is in her pocket. The protocol is in a drawer.

*What if the phone could **be** the doctor?*

## What we built

Three surfaces, two tiers, one Gemma 4 family — **Apache 2.0 end-to-end**.

**Tier 0 — The phone.** A Flutter Android app running **Gemma 4 E2B (2.58 GB) fully offline** on a $60 Samsung A53. Twelve clinical skills. Voice in any language (offline STT + TTS on Android-native CPU). Photo-based vision for alertness, sunken eyes, visible ribs, edema. Deterministic WHO IMCI classification. Treatment instructions read aloud in the caregiver's language. **Airplane-mode, forever.**

**Tier 1 — The village clinic server.** FastAPI loading our **fine-tuned Gemma 4 E4B + LoRA** on the ICBHI 2017 respiratory-sound dataset. A nurse drops a 30-second auscultation; the server returns a breath-sound classification *and* a clinical reasoning note grounded in WHO IMCI.

**The web clinical portal** — Next.js 16, browser-native audio capture, live connection-health probe, the **AI Clinical Note** as the result-card centerpiece. Live at **[malaika-delta.vercel.app](https://malaika-delta.vercel.app/)**.

## How Gemma 4 powers every layer

Every capability below is unique to Gemma 4 and could not be substituted on this hardware.

- **Per-Layer Embeddings (E2B).** Fits text + vision + multilingual reasoning in 2.58 GB on a $60 Android. Benchmarked on the same A53: Llama 3.2 1B/3B has no vision; 11B-Vision (~8 GB) doesn't fit; Phi-3.5-Vision is English-leaning; Qwen 2.5-VL lacks African coverage. **Only Gemma 4 E2B meets all four constraints — size, vision, multilingual, on-device speed.**
- **Native multimodal vision (SigLIP).** Six on-phone vision skills *and* mel-spectrogram classification on the clinic server — **one model sees a photo of a child and a spectrogram of breath sounds.**
- **Native multilingual (140+ languages).** Swahili, Hausa, Hindi, Bengali — Gemma understands her. **No translation pipeline.**
- **Agentic tool use.** A 12-skill `SkillRegistry`, structured event emission, typed `BeliefState`. Gemma 4's native function-calling makes IMCI orchestration work on a phone.
- **Apache 2.0 open source.** Phone and clinic both hold the weights. **No vendor API.**

## Two tiers of care. One architecture.

The phone always works, alone, with no internet, ever. The clinic server augments — adding what the phone honestly cannot do: listen to a child's chest. When the phone reaches Wi-Fi, it offloads spectrogram analysis to the clinic's own hardware, **never anyone else's cloud**. Same Gemma 4 family. Same on-device privacy. Built by two people in thirty-six days.

## The defining technical move: AI Clinical Note

After the auscultation classifier returns *abnormal: 91%*, the **same Gemma 4 model runs a second pass** with a senior-nurse-mentoring-a-junior-colleague prompt and produces a clinical reasoning note for the chart, grounded in WHO IMCI, naming the next deterministic protocol step:

> *"Crackles auscultated bilaterally with intermittent expiratory wheeze, consistent with adventitious lower-respiratory sounds. Per WHO IMCI, count respiratory rate over 60 seconds and examine for chest indrawing; if RR exceeds the age-adjusted threshold or any general danger sign is present, classify as severe pneumonia and refer urgently."*

One model. One session. **A chart-grade reasoning artifact**, not just a probability.

## Fine-tuning that means something

**Unsloth QLoRA on Gemma 4 E4B**, trained on ICBHI 2017 audio → mel-spectrogram → vision pipeline. **85% crackle detection on a held-out patient cohort** the model never saw. Adapter: [`Vimal0703/malaika-breath-sounds-E4B-merged`](https://huggingface.co/Vimal0703/malaika-breath-sounds-E4B-merged). Reproducible from `notebooks/06_unsloth_binary_phase1.ipynb`. **Hackathon-grade, not FDA-cleared.**

## Where AI stops, and code begins

Every WHO IMCI classification — *severe pneumonia*, *some dehydration*, *moderate wasting* — is a **hard-coded threshold** in deterministic code, never a probability from the model. If WHO updates a threshold, we change one line. *We do not let an AI decide whether a child lives or dies.* The AI's job is the human part — listening, looking, translating. The medicine belongs to the World Health Organization.

Backed by **104+ passing tests, 21/21 WHO IMCI golden scenarios**, three-layer security guards, 31 versioned prompts, per-step observability. We do not claim video breathing-rate (GPU constraints), real-time monitoring, or FDA clearance — every honest limit is in [`REASONS_WE_WILL_FAIL.md`](https://github.com/Vimalk0703/Google-Gemma4-good-hackathon-VimalXMark/blob/main/REASONS_WE_WILL_FAIL.md). Every number is cited in [`SOURCES.md`](https://github.com/Vimalk0703/Google-Gemma4-good-hackathon-VimalXMark/blob/main/SOURCES.md). **We came with receipts.**

## Why open source

We could have built this for agriculture, education, climate, finance. **We chose children** — because we don't know which of those 4.9 million lost every year would have become the next **Sundar Pichai**, the boy from a two-room home in Tamil Nadu who today runs the company that built the model in this app; the next **Wangari Maathai**, the village girl from Kenya who won the Nobel Peace Prize; the next **Yusuf Hamied**, the Indian chemist whose generic medicines reached the African continent that branded pricing never would. **Everyone deserves a place in this world.**

We built it on **Gemma** because the AI that decides whether a child lives must not belong to a company. *It has to belong to everyone.* Apache 2.0 is not a slogan — it is a file you can read, modify, and ship.

## The next thirty-nine seconds

Anywhere close to the 15% IMCI number on pneumonia and diarrhea is **~175,000 children a year — 480 every day — still in their mothers' arms**. A projection from human-delivered IMCI, not a measurement. We say it that way until we have measured it.

**Pneumonia kills a child every thirty-nine seconds. The next thirty-nine seconds belong to us — and to every developer who picks this up tomorrow, in any village, in any language, on any phone.**

— *Vimal & Mark, May 2026. Apache 2.0.*

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
