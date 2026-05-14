# Malaika — putting the WHO's child-survival protocol in a sixty-dollar phone

> **A child dies of pneumonia every thirty-nine seconds.**<sup>[3](REFERENCES.md#ref-3)</sup> The medicine costs five cents. The protocol is thirty years old. *It still isn't reaching her.* Malaika puts it in her hand.

*👉 If you have twelve minutes, please watch the [full storytelling film](https://youtu.be/2p932LTc_wE) — it is a must for the full picture. The [3-minute pitch](https://youtu.be/Gf415IgJr0s) is in the media gallery.*

---

## The problem isn't medicine. It's distribution.

In 2024, **4.9 million children** under five did not see their fifth birthday.<sup>[1](REFERENCES.md#ref-1)</sup> Fifty-eight percent in Sub-Saharan Africa. Of those, **1.17 million** were killed by two diseases — pneumonia and diarrhea.<sup>[2](REFERENCES.md#ref-2)</sup>

The numbers persist not because the medicine fails, but because the medicine never arrives. The WHO wrote a protocol for these conditions — **Integrated Management of Childhood Illness (IMCI)** — in the mid-1990s.<sup>[5](REFERENCES.md#ref-5)</sup> A Cochrane review found that fully implemented IMCI cuts under-five mortality by **15%** (RR 0.85; 95% CI 0.78–0.93; n=65,570).<sup>[6](REFERENCES.md#ref-6)</sup>

But to learn IMCI a nurse trains for eleven days.<sup>[7](REFERENCES.md#ref-7)</sup> Africa has **1.5 health workers** per thousand people; the WHO minimum is 4.45.<sup>[12](REFERENCES.md#ref-12)</sup> By 2030 the shortage will exceed **6 million**.<sup>[13](REFERENCES.md#ref-13)</sup> The median rural-Uganda mother waits **two days** before seeking pneumonia care.<sup>[8](REFERENCES.md#ref-8)</sup> For pneumonia, two days is the entire window between life and death.

The protocol that could save a million children a year is sitting in a manual, in a drawer, in a clinic she will never reach. That is not a medical problem. **It is a distribution problem.**

---

## Umlazi

A peer-reviewed case-series from a township outside Durban documents **five infants who died en route home from hospital**.<sup>[10](REFERENCES.md#ref-10)</sup> A young mother is discharged with her newborn. Halfway home on the bus, the baby starts breathing too fast. She knows something is wrong. What she doesn't know is *how* wrong — whether tonight is *get off this bus* or *see how he sleeps*.

That second kind of knowing has a name: **the WHO IMCI protocol**. That night, it was sitting in a manual, in a drawer, in a clinic she couldn't afford to ride to. She has no bus fare. She holds her child. She prays. By the time she steps off, the baby has died.

What was missing was never only the medicine. It was the **certainty** of knowing what tonight is — the certainty to beg the driver, wake a neighbour, walk the road. *It is everything she did not have.*

---

## The paradox

**The phone got to the village before the doctor did.** **489 million** unique mobile subscribers in Sub-Saharan Africa.<sup>[14](REFERENCES.md#ref-14)</sup> Entry-level Android handsets at **~$60**.<sup>[16](REFERENCES.md#ref-16)</sup> The hardware is in her pocket. The protocol is in a drawer.

*What if the phone could **be** the doctor?*

---

## What we built

Three surfaces, two tiers, one Gemma 4 family — **Apache 2.0 end-to-end**.

### Tier 0 — The phone

A Flutter Android app running **Gemma 4 E2B (2.58 GB) fully offline** on a $60 Samsung A53. Twelve clinical skills. Voice in any language (offline STT + TTS on Android-native CPU). Photo-based vision for alertness, sunken eyes, visible ribs, edema. Deterministic WHO IMCI classification. Treatment instructions read aloud in the caregiver's language. **Airplane-mode, forever.**

### Tier 1 — The village clinic server

FastAPI loading our **fine-tuned Gemma 4 E4B + LoRA** on the ICBHI 2017 respiratory-sound dataset. A nurse drops a 30-second auscultation; the server returns a breath-sound classification *and* a clinical reasoning note grounded in WHO IMCI.

### The web clinical portal

Next.js 16, browser-native audio capture, live connection-health probe, the **AI Clinical Note** as the result-card centerpiece. Live at **[malaika-delta.vercel.app](https://malaika-delta.vercel.app/)**.

---

## How Gemma 4 powers every layer

Every capability below is unique to Gemma 4 and could not be substituted on this hardware.

- **Per-Layer Embeddings (E2B).**<sup>[18](REFERENCES.md#ref-18)</sup> Fits text + vision + multilingual reasoning in 2.58 GB on a $60 Android. Benchmarked on the same A53: Llama 3.2 1B/3B has no vision; 11B-Vision (~8 GB) doesn't fit; Phi-3.5-Vision is English-leaning; Qwen 2.5-VL lacks African coverage. **Only Gemma 4 E2B meets all four constraints — size, vision, multilingual, on-device speed.**
- **Native multimodal vision (SigLIP).** Six on-phone vision skills *and* mel-spectrogram classification on the clinic server — **one model sees a photo of a child and a spectrogram of breath sounds.**
- **Native multilingual (140+ languages).** Swahili, Hausa, Hindi, Bengali — Gemma understands her. **No translation pipeline.**
- **Agentic tool use** (~12× improvement over Gemma 3).<sup>[18](REFERENCES.md#ref-18)</sup> A 12-skill `SkillRegistry`, structured event emission, typed `BeliefState`. Gemma 4's native function-calling makes IMCI orchestration work on a phone. *In plain terms:* the model picks the next clinical question based on what is already known about the child — exactly how an experienced nurse works through an IMCI assessment.
- **Apache 2.0 open source.**<sup>[20](REFERENCES.md#ref-20)</sup> Phone and clinic both hold the weights. **No vendor API.**

---

## Two tiers of care. One architecture.

The phone always works, alone, with no internet, ever. The clinic server augments — adding what the phone honestly cannot do: listen to a child's chest. When the phone reaches Wi-Fi, it offloads spectrogram analysis to the clinic's own hardware, **never anyone else's cloud**. Same Gemma 4 family. Same on-device privacy. Built by two people in thirty-six days.

---

## The defining technical move: AI Clinical Note

After the auscultation classifier returns *abnormal: 91%*, the **same Gemma 4 model runs a second pass** with a senior-nurse-mentoring-a-junior-colleague prompt and produces a clinical reasoning note for the chart, grounded in WHO IMCI, naming the next deterministic protocol step:

> *"Crackles auscultated bilaterally with intermittent expiratory wheeze, consistent with adventitious lower-respiratory sounds. Per WHO IMCI, count respiratory rate over 60 seconds and examine for chest indrawing; if RR exceeds the age-adjusted threshold or any general danger sign is present, classify as severe pneumonia and refer urgently."*

One model. One session. **A chart-grade reasoning artifact**, not just a probability.

---

## Fine-tuning that means something

**Unsloth QLoRA**<sup>[25](REFERENCES.md#ref-25)</sup> **on Gemma 4 E4B**, trained on the ICBHI 2017 Respiratory Sound Database<sup>[21](REFERENCES.md#ref-21)</sup> audio → mel-spectrogram → vision pipeline. **85% crackle detection on a held-out patient cohort** the model never saw. Adapter: [`Vimal0703/malaika-breath-sounds-E4B-merged`](https://huggingface.co/Vimal0703/malaika-breath-sounds-E4B-merged). Reproducible from `notebooks/06_unsloth_binary_phase1.ipynb`. **Hackathon-grade, not FDA-cleared.**

---

## Where AI stops, and code begins

Every WHO IMCI classification — *severe pneumonia*, *some dehydration*, *moderate wasting* — is a **hard-coded threshold** in deterministic code, never a probability from the model. If WHO updates a threshold, we change one line. *We do not let an AI decide whether a child lives or dies.* The AI's job is the human part — listening, looking, translating. The medicine belongs to the World Health Organization.

Backed by **104+ passing tests, 21/21 WHO IMCI golden scenarios**, three-layer security guards, 31 versioned prompts, per-step observability. We do not claim video breathing-rate (GPU constraints), real-time monitoring, or FDA clearance — every honest limit is in [`HONEST_LIMITS.md`](https://github.com/Vimalk0703/Google-Gemma4-good-hackathon-VimalXMark/blob/main/HONEST_LIMITS.md). Every number is cited in [`SOURCES.md`](https://github.com/Vimalk0703/Google-Gemma4-good-hackathon-VimalXMark/blob/main/SOURCES.md). **We came with receipts.**

---

## Why open source

We could have built this for agriculture, education, climate, finance. **We chose children** — because we don't know which of those 4.9 million lost every year would have become the next **Sundar Pichai**, the boy from a two-room home in Tamil Nadu who today runs the company that built the model in this app; the next **Wangari Maathai**, the village girl from Kenya who won the Nobel Peace Prize; the next **Yusuf Hamied**, the Indian chemist whose generic medicines reached the African continent that branded pricing never would. **Everyone deserves a place in this world.**

We built it on **Gemma** because the AI that decides whether a child lives must not belong to a company. *It has to belong to everyone.* Apache 2.0 is not a slogan — it is a file you can read, modify, and ship.

---

## The next thirty-nine seconds

Anywhere close to the 15% IMCI number<sup>[6](REFERENCES.md#ref-6)</sup> on pneumonia and diarrhea is **~175,000 children a year — 480 every day — still in their mothers' arms**. A projection from human-delivered IMCI, not a measurement. We say it that way until we have measured it.

**Pneumonia kills a child every thirty-nine seconds.<sup>[3](REFERENCES.md#ref-3)</sup> The next thirty-nine seconds belong to us — and to every developer who picks this up tomorrow, in any village, in any language, on any phone.**

— *Vimal & Mark, May 2026. Apache 2.0.*

---

*Every numbered superscript above resolves to the canonical AMA-style reference in [`REFERENCES.md`](REFERENCES.md). Companion claim-first index: [`SOURCES.md`](SOURCES.md).*
