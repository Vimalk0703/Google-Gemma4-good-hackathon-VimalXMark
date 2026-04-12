# Malaika — The AI That Saves Children's Lives

> *"Malaika" means "Angel" in Swahili*

**Competition**: Gemma 4 Good Hackathon (Kaggle + Google DeepMind)
**Track**: Health & Sciences
**Prize Target**: Main 1st ($50K) + Health & Sciences ($10K) + Unsloth ($10K) = **$70,000**
**Team**: Vimal Kumar + Mark D. Hei Long

---

## The Problem

### 4.9 million children died before their fifth birthday last year.

That's one child every 6 seconds.

Source: [WHO/UNICEF — March 18, 2026](https://www.who.int/news/item/18-03-2026-progress-in-reducing-child-deaths-slows-as-4.9-million-children-die-before-age-five) (published 3 weeks ago)

| Statistic | Number | Source |
|-----------|--------|--------|
| Under-5 deaths per year | 4.9 million | WHO/UNICEF March 2026 |
| Projected deaths by 2030 | 27.3 million more | WHO/UNICEF March 2026 |
| Deaths in Sub-Saharan Africa | 58% of all | WHO/UNICEF March 2026 |
| Newborn deaths (first 28 days) | 2.3 million | WHO/UNICEF March 2026 |
| Largest infectious killer | Pneumonia | WHO |
| Other top killers | Diarrhea, malaria | WHO |
| Cost of amoxicillin (treats pneumonia) | $0.50 | WHO Essential Medicines |
| ORS + zinc reduces diarrhea mortality | by 93% | WHO IMCI evidence |
| Deaths from severe acute malnutrition | 100,000+ children/year | WHO/UNICEF March 2026 |

### The Outrageous Part

**Most of these deaths are preventable with proven, low-cost interventions.**

The WHO created [IMCI (Integrated Management of Childhood Illness)](https://www.who.int/teams/maternal-newborn-child-adolescent-health-and-ageing/child-health/integrated-management-of-childhood-illness/) — a step-by-step clinical protocol that tells you EXACTLY how to assess a sick child and what to do. It's adopted by 100+ countries. It's proven to save lives.

**But less than 25% of health facilities have enough workers trained in it.**

The knowledge exists. The children keep dying. Because the protocol is stuck in English-language clinical manuals while mothers are alone with sick children at 2am in villages with no clinic, no internet, and no trained health worker.

### Why This Hasn't Been Solved

- Training a community health worker in IMCI takes months
- There aren't enough CHWs — and the ones that exist are concentrated in cities
- The protocol requires clinical skills: counting breathing rate, recognizing chest indrawing, classifying breath sounds
- Telemedicine requires internet — 2.6 billion people have none
- Existing health apps assume literacy, English, and connectivity

---

## The Solution

### Malaika: The WHO IMCI protocol, brought to life as a multimodal AI on every phone.

**This is NOT a chatbot. This is a medical instrument.**

Like an AED (defibrillator) doesn't "diagnose" — it implements a protocol that saves lives. Malaika doesn't "play doctor" — it implements the WHO's proven, gold-standard IMCI assessment protocol through the phone's camera, microphone, and voice.

A mother's child is sick. She's scared. No clinic. No internet. She opens Malaika.

**The AI doesn't wait for her to type. It SPEAKS to her in her language.**

---

### The Assessment Flow

#### Step 1 — LOOK (Gemma 4 Vision)
> "Hold the phone so I can see your child's chest."

- Camera watches the child's chest → **counts breathing rate in real-time** from chest wall movement
- Detects **chest indrawing** (subcostal retraction — a WHO danger sign)
- Assesses **skin color**: cyanosis (blue = low oxygen), jaundice (yellow = liver), pallor (pale = anemia)

#### Step 2 — LISTEN (Gemma 4 Native Audio)
- Microphone analyzes **breathing sounds**: wheezing, grunting, stridor
- Each sound maps to a specific IMCI clinical indicator
- Detects **cough patterns** and severity

#### Step 3 — ASK (Voice Conversation)
> "Is your child able to drink or breastfeed?"
> "Has your child vomited everything today?"
> "Has your child had convulsions?"

- All in HER language — Gemma 4 supports 140+ languages
- She SPEAKS the answers — no typing, no literacy needed
- Follow-up questions adapt based on previous answers (agentic reasoning)

#### Step 4 — ASSESS (Agentic Protocol Engine)
- Gemma 4 runs the **FULL IMCI protocol** as a chain of function calls
- Multi-step, branching decision tree:
  - Breathing assessment → Cough/pneumonia classification
  - Diarrhea assessment → Dehydration classification
  - Fever assessment → Malaria risk classification
  - Nutrition assessment → Malnutrition screening
  - Danger sign aggregation → Overall severity
- This is exactly what Gemma 4's **1,200% improvement in agentic tool use** was built for

#### Step 5 — ACT
Classification with clear next steps:

- 🟢 **Treat at home**: Step-by-step voice instructions
  - *"Mix one packet of ORS in one liter of clean water. Give small sips every 5 minutes."*
  - Dosing guidance for available medications
  - When to check again, what warning signs to watch for
- 🟡 **Refer to clinic**: What to do while waiting, what to tell the health worker
- 🔴 **URGENT — Go NOW**: What to do during transport, pre-arrival instructions

---

## Why This is Groundbreaking

### It's not AI replacing doctors. It's AI delivering a PROVEN protocol to where doctors can't reach.

| What exists today | What Malaika does |
|-------------------|-------------------|
| IMCI on paper — needs months of CHW training | IMCI as interactive AI — needs zero training |
| Requires manually counting breaths with a timer | Camera counts breathing rate automatically in real-time |
| Requires recognizing chest indrawing by eye | Vision AI detects it automatically |
| Requires a trained ear for abnormal breath sounds | Audio AI classifies wheezing, grunting, stridor |
| Only works if a trained CHW is present | Works for any mother, alone, at 2am |
| Written in English/French clinical manuals | In YOUR language, spoken aloud |
| Telemedicine needs internet connectivity | Fully offline — runs on-device |
| Training takes months, CHWs forget over time | AI is consistent, never forgets a step |
| Equipment costs $1,000s for pulse oximeters, timers | Uses the phone you already own |

### The disruption

**Months of medical training → an app. Thousands of dollars in equipment → a phone camera.**

---

## Technical Architecture

```
┌─────────────────────────────────────────────────────┐
│                   MALAIKA CORE                       │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │  Camera   │  │   Mic    │  │  Voice   │          │
│  │  Stream   │  │  Stream  │  │  Input   │          │
│  └─────┬─────┘  └─────┬────┘  └─────┬────┘         │
│        │              │              │               │
│  ┌─────▼─────┐  ┌─────▼────┐  ┌─────▼────┐         │
│  │  VISION   │  │  AUDIO   │  │ LANGUAGE │          │
│  │  ENGINE   │  │  ENGINE  │  │  ENGINE  │          │
│  └─────┬─────┘  └─────┬────┘  └─────┬────┘         │
│        └───────────────┼─────────────┘               │
│                        ▼                             │
│  ┌─────────────────────────────────────────┐        │
│  │        GEMMA 4 E4B — REASONING CORE      │        │
│  │    (Multimodal Fusion + IMCI Protocol)    │        │
│  └──────────────────┬──────────────────────┘        │
│                     ▼                                │
│  ┌─────────────────────────────────────────┐        │
│  │      IMCI PROTOCOL ENGINE               │         │
│  │      (Agentic Function Calling)          │         │
│  │                                          │         │
│  │  ┌────────┐ ┌────────┐ ┌────────┐       │        │
│  │  │BREATHE │ │DIARRHEA│ │ FEVER  │       │        │
│  │  │ASSESS  │ │ASSESS  │ │ASSESS  │       │        │
│  │  └────────┘ └────────┘ └────────┘       │        │
│  │  ┌────────┐ ┌────────┐ ┌────────┐       │        │
│  │  │NUTRITN │ │DANGER  │ │SEVERITY│       │        │
│  │  │ASSESS  │ │ SIGNS  │ │CLASSIFY│       │        │
│  │  └────────┘ └────────┘ └────────┘       │        │
│  └──────────────────┬──────────────────────┘        │
│                     ▼                                │
│  ┌─────────────────────────────────────────┐        │
│  │         RESPONSE ENGINE                  │        │
│  │   Voice (TTS) + Visual + Instructions    │        │
│  │        In user's language                │        │
│  └─────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────┘
```

### Specialized Tools (10+)

| Tool | What It Does | Gemma 4 Feature |
|------|-------------|-----------------|
| `count_breathing_rate()` | Real-time chest wall movement analysis from video | Vision (E4B) |
| `detect_chest_indrawing()` | Subcostal retraction detection | Vision (E4B) |
| `analyze_skin_color()` | Cyanosis, jaundice, pallor detection | Vision (E4B) + Unsloth fine-tuned |
| `classify_breath_sounds()` | Wheezing, grunting, stridor classification | Native Audio (E4B) + Unsloth fine-tuned |
| `assess_cough()` | Cough pattern analysis (duration, severity) | Native Audio (E4B) |
| `collect_symptoms()` | Voice-based symptom questionnaire in local language | Native Audio + multilingual |
| `assess_dehydration()` | Guided skin pinch test via camera + voice | Vision + voice guidance |
| `classify_pneumonia()` | IMCI pneumonia decision tree | Function calling chain |
| `classify_diarrhea()` | IMCI diarrhea/dehydration decision tree | Function calling chain |
| `classify_fever()` | IMCI fever/malaria decision tree | Function calling chain |
| `assess_nutrition()` | Visual MUAC estimation + guided measurement | Vision + voice |
| `aggregate_danger_signs()` | Multi-signal fusion → overall severity | Agentic reasoning |
| `generate_treatment_plan()` | Step-by-step voice instructions for home treatment | TTS + function calling |
| `generate_referral()` | Urgency classification + transport guidance | Agentic reasoning |

### Fine-Tuning Strategy (Mark's RTX 3060, 12GB VRAM)

| LoRA Adapter | Training Data | Purpose |
|-------------|---------------|---------|
| Respiratory sounds | ICBHI 2017 dataset (920 recordings, open) | Classify wheezing, crackles, stridor, normal |
| Skin assessment | Open dermatology + neonatal datasets | Jaundice, cyanosis, pallor detection |
| African languages | WAXAL (Google, 21 languages, 11K hours) | Speech understanding for underserved languages |
| IMCI reasoning | WHO clinical guidelines (public domain) | Structured protocol following |

Gemma 4 E2B LoRA fine-tuning requires 8-10GB VRAM — fits on the RTX 3060 (12GB).
Multiple adapters loaded dynamically by the protocol engine.

---

## Why Malaika Wins This Competition

### 1. The Problem is Undeniable
4.9 million children/year. WHO report from 3 weeks ago. Fresh headlines. Every judge will have seen this number. You can't argue this isn't important.

### 2. It's NOT a Chatbot
The blog post warned against "generic AI doctor chatbot." Malaika is fundamentally different — it's a **protocol-based medical instrument** implementing WHO's proven IMCI standard. Like an AED for childhood illness. The AI doesn't hallucinate medical advice — it executes a validated decision tree enhanced by multimodal sensing.

### 3. It Uses EVERY Gemma 4 Capability
| Capability | How Malaika Uses It |
|-----------|-------------------|
| Vision | Breathing rate from video, chest indrawing, skin color |
| Native Audio | Breath sound classification, cough analysis |
| Multilingual | Voice interface in 140+ languages |
| Function Calling | IMCI protocol as agentic workflow chain |
| On-device | Runs entirely on phone, no internet |
| Reasoning | Multi-factor severity classification |

No other hackathon submission will use this many Gemma 4 features simultaneously.

### 4. It Matches the Winning Pattern
Previous Gemma 3n winners had: real user, offline-first, multimodal, emotionally compelling video. Malaika has all four — at a BIGGER scale.

### 5. Google Alignment is Perfect
- Google's #1 social good priority is health AI (MedGemma, $30M health funding)
- WAXAL dataset (Google's own, released Feb 2026) for African languages
- Edge AI / on-device is Gemma 4's core thesis
- Sundar Pichai: "democratize access from the start"

### 6. Technical Depth Matches Our Geotab Standard
Geotab had 17 AI tools. Malaika has 14+ specialized tools, real-time video + audio processing, multimodal fusion, agentic protocol execution, multiple LoRA adapters. The technical depth is there.

### 7. The Video Will Make Judges Cry
A mother. A sick child. Night. No help. She opens her phone. The AI speaks her language. It watches her child breathe. It listens. It guides her. The child survives. That's the video that wins.

### 8. Nobody Else is Building This
No existing competition submission combines real-time video breathing analysis + audio breath classification + agentic clinical protocol execution. The AFASIA and VillageDoc submissions are in different territory entirely.

### 9. Fresh WHO Data = Timeliness
The March 2026 report means this is IN THE NEWS. Judges will connect our submission to headlines they've seen. Relevance matters.

### 10. Open Source is the ONLY Way to Solve This
This can't be a cloud AI product — there's no internet where children are dying. This can't be a proprietary product — families can't afford subscriptions. It HAS to be open source, on-device, free. Gemma 4 under Apache 2.0 is literally the only model that makes this possible at this quality level.

---

## The Narrative Arc (Mark's Framework)

### 1. Open source model constraints → What it CAN do
"They said a 4-billion-parameter model can't do real medical assessment. We showed it counting a child's breaths, hearing their lungs, and running a clinical protocol — all on a $100 phone with no internet."

### 2. People impacted the most
4.9 million children/year. Mothers alone with sick children in villages without doctors. The most vulnerable people on earth.

### 3. How to apply AI in a way that has never been done before
Real-time multimodal clinical assessment via phone sensors, implementing a WHO gold-standard protocol, in any language, offline. This has literally never existed.

---

## The Video Script (3 Minutes)

### [0:00 - 0:15] The Number
Black screen. White text, one number at a time:

> 4.9 million.
> That's how many children died before their fifth birthday last year.
> One child. Every six seconds.

### [0:15 - 0:30] The Gap
Split screen: LEFT — WHO headquarters, shelves of IMCI manuals, clinical protocols, English text. RIGHT — a village at night. A mother holding a feverish child. No electricity. No clinic for 100km.

> "The World Health Organization published the exact steps to save them.
> But the knowledge is here [LEFT].
> And the children are here [RIGHT]."

### [0:30 - 0:45] The Contrast (Mark's Idea)
Quick montage: headlines and tweets — "open source models can't match GPT-4", "small models are toys", "you need billions of parameters for anything useful."

> "They said open source models couldn't do real-world work.
> We said: hold our phone."

### [0:45 - 1:15] The Turn
The mother opens Malaika. The AI speaks to her in her language.

Show the phone screen: clean, simple interface. No text to read. A voice guides her.

> "Hold the phone so I can see your child's chest."

### [1:15 - 2:00] The Assessment (Technical Showcase)
This is the "wow" sequence. Show each modality working:

**VISION**: Camera view of child's chest. Real-time breathing rate counter overlay: "56 breaths/min" (normal range shown: 30-50). Flashing warning.

**AUDIO**: Waveform visualization. The AI detects grunting sounds. Audio classification display: "Grunting detected — respiratory distress indicator."

**VOICE**: The mother answers questions. Her words appear as the AI understands them. In her language.

**PROTOCOL**: Split screen showing the IMCI decision tree being traversed in real-time. Each assessment step completing. Branches lighting up. Building toward classification.

This 45-second sequence shows ALL of Gemma 4's capabilities in action simultaneously. This is the "I didn't know you could do that" moment.

### [2:00 - 2:20] The Verdict
🔴 URGENT — likely severe pneumonia.

The AI speaks calmly:
> "Your child's breathing is dangerously fast and I can hear sounds that suggest pneumonia. This is treatable but urgent. Here's what to do right now..."

Step-by-step voice instructions appear on screen as the AI speaks them.

### [2:20 - 2:40] The Scale
Quick montage: different mothers, different countries, different languages. Same app. Same AI. Same lifesaving moment.

Kenya. India. Bangladesh. Nigeria. Guatemala.

> "4.9 million children. The knowledge to save them exists.
> Now it's in every mother's hands."

### [2:40 - 3:00] The Close
The mother from the opening. It's morning. She's at the clinic with her child. The child is being treated.

> "Malaika.
> The WHO's lifesaving protocol, powered by Gemma 4.
> Any language. Any phone. No internet. Free.
> Because no child should die from a disease we know how to treat."

Logo. URL. QR code.

---

## Accessibility — Works for Everyone

| User Group | How Malaika Serves Them |
|-----------|------------------------|
| **Illiterate caregivers** | Entirely voice-based — no reading or typing needed |
| **Visually impaired users** | Audio-first interface, spoken instructions |
| **Hearing impaired users** | Visual indicators, text display option |
| **Remote villages** | Fully offline — no internet required after download |
| **Low-income families** | Free, runs on basic Android phones ($100+) |
| **Non-English speakers** | 140+ languages, fine-tuned for African languages via WAXAL |
| **Community health workers** | Enhances their capabilities, fills training gaps |

---

## Sprint Plan (37 Days — Deadline May 18, 2026)

### Phase 1: Core Engine (Days 1-10)
- Set up Gemma 4 E4B via Ollama
- Build IMCI protocol engine (function calling chain)
- Implement voice conversation interface
- Basic breathing rate from video (MVP)

### Phase 2: Multimodal Sensing (Days 11-20)
- Fine-tune respiratory sound classifier (Unsloth + ICBHI dataset)
- Fine-tune skin color assessment
- Fine-tune African language support (WAXAL)
- Implement chest indrawing detection
- Build multimodal fusion logic

### Phase 3: Polish + Demo (Days 21-30)
- Mobile-friendly web interface
- Live demo deployment
- End-to-end testing across scenarios
- Multilingual testing

### Phase 4: Submission (Days 31-37)
- Record 3-minute video
- Write Kaggle writeup (1,500 words max)
- Public GitHub repo + documentation
- Live demo URL
- Media gallery + cover image
- Submit on Kaggle

---

## Google Open Data & Tools We'll Use

| Resource | What It Gives Us |
|----------|-----------------|
| **WAXAL Dataset** (Google, Feb 2026) | 11,000+ hours of speech in 21 African languages |
| **MedGemma research** (Google) | Medical AI architecture patterns and benchmarks |
| **MediaPipe** (Google) | Face/body tracking for visual assessment |
| **Google AI Edge Gallery** | On-device deployment patterns |
| **LiteRT-LM** (Google, April 2026) | Production inference framework |
| **ICBHI 2017** (open) | Respiratory sound recordings for fine-tuning |
| **WHO IMCI protocol** (public domain) | Clinical decision tree — the gold standard |

---

## Competition Alignment Check

| Requirement | How We Meet It |
|------------|---------------|
| Must use Gemma 4 centrally | Gemma 4 E4B is the ENTIRE brain — vision, audio, reasoning, function calling |
| Kaggle Writeup (1,500 words) | Technical architecture + impact narrative |
| Video (3 min, YouTube) | Emotionally compelling demo with real scenarios |
| Public code repository | GitHub, well-documented, reproducible |
| Live demo | Web app + phone demo, publicly accessible |
| Cover image + media gallery | Screenshots, architecture diagrams, impact visuals |
| Track selection | Health & Sciences |
| Also eligible for | Unsloth Special Technology Prize ($10K) |

---

## The One-Liner

**"4.9 million children die every year from treatable diseases. The WHO knows exactly how to save them. Malaika puts that knowledge in every mother's hands — in her language, through her phone, powered by Gemma 4. No internet. No training. No cost."**

---

*Prepared by Vimal Kumar & Mark D. Hei Long — April 2026*
