# Malaika — The AI That Saves Children's Lives

> *"Malaika" means "Angel" in Swahili*

**4.9 million children died before their fifth birthday last year. Most from diseases we know how to treat.**

Malaika puts the WHO's proven [IMCI protocol](https://www.who.int/teams/maternal-newborn-child-adolescent-health-and-ageing/child-health/integrated-management-of-childhood-illness/) into every mother's hands — through her phone's camera, microphone, and voice — powered entirely by **Gemma 4**, fully offline, in her language.

This is **not a chatbot**. This is a medical instrument — like an AED for childhood illness.

---

## The Problem

| Stat | Number | Source |
|------|--------|--------|
| Under-5 deaths per year | **4.9 million** | [WHO/UNICEF, March 2026](https://www.who.int/news/item/18-03-2026-progress-in-reducing-child-deaths-slows-as-4.9-million-children-die-before-age-five) |
| Deaths in Sub-Saharan Africa | 58% of all | WHO/UNICEF |
| Largest infectious killer | Pneumonia | WHO |
| Cost of treatment (amoxicillin) | $0.50 | WHO Essential Medicines |
| Health facilities with trained IMCI workers | < 25% | WHO |
| People without internet | 2.6 billion | ITU |

The WHO created a step-by-step protocol (IMCI) that tells you exactly how to assess a sick child and what to do. It's adopted by 100+ countries. It saves lives.

**But the protocol is stuck in English-language clinical manuals while mothers are alone with sick children at 2am in villages with no clinic, no internet, and no trained health worker.**

---

## What Malaika Does

### Step 1 — LOOK (Gemma 4 Vision)
> "Hold the phone so I can see your child's chest."

- Camera counts **breathing rate** from chest wall movement
- Detects **chest indrawing** (a WHO danger sign)
- Assesses **skin color**: jaundice, cyanosis, pallor
- Evaluates **visible wasting** (severe malnutrition)

### Step 2 — LISTEN (Gemma 4 Audio)
- Classifies **breath sounds**: wheezing, grunting, stridor
- Detects **cough patterns** and severity
- Analyzes **heart sounds** via phone mic (experimental MEMS module)

### Step 3 — ASK (Voice Conversation)
> "Has your child had diarrhea? For how many days?"

- Speaks to the caregiver **in her language**
- No typing, no literacy needed — fully voice-based
- Adapts follow-up questions based on previous answers

### Step 4 — ASSESS (IMCI Protocol Engine)
Runs the complete WHO IMCI decision tree:
- Danger signs check
- Breathing/pneumonia assessment
- Diarrhea/dehydration classification
- Fever/malaria assessment
- Nutrition/malnutrition screening
- Aggregate severity classification

### Step 5 — ACT (Treatment Plan)
- :red_circle: **URGENT** — Go to facility NOW, what to do during transport
- :yellow_circle: **Refer** — Go within 24 hours, home care while waiting
- :green_circle: **Treat at home** — Step-by-step instructions in her language

---

## How Gemma 4 Powers Everything

This is NOT "we used Gemma 4 as a chatbot." Every core capability comes from Gemma 4:

| Gemma 4 Capability | What It Enables | Why Only Gemma 4 |
|---------------------|-----------------|------------------|
| Native vision on-device | Camera sees chest indrawing, jaundice, wasting | No other open model does multimodal vision on a phone at this quality |
| Native audio on-device | Mic hears breath sounds, understands speech | Built-in audio encoder — not a separate pipeline |
| Native function calling | IMCI protocol steps as tool calls | 1200% improvement over Gemma 3 in agentic tool use |
| 140+ languages | Caregiver speaks Swahili, Hindi, Hausa — AI understands | Built into the model, not an add-on translation layer |
| Apache 2.0 license | Free to deploy in any country, any clinic, any phone | No restrictive license |
| Runs in < 3GB on phone | Works on phones already in billions of pockets | E2B: 2.58GB disk, 676MB RAM |

### What is NOT Gemma 4

| Component | What It Is | Why It's Fine |
|-----------|-----------|---------------|
| IMCI State Machine | Deterministic Python code with WHO thresholds | This is a calculator, not intelligence |
| MMS-TTS | Speaks text Gemma generated aloud | Like a speaker — the intelligence is Gemma's |
| OpenCV | Extracts frames from video | Like opening a file — the analysis is Gemma's |
| Gradio UI | Displays results, captures input | A window — what you see through it is Gemma |

---

## Architecture

```
PHONE (Video proof)                    DEMO MACHINE (Live demo)
+--------------------+                +-----------------------------+
|  Gemma 4 E2B       |                |  Gemma 4 E4B (fine-tuned)   |
|  via LiteRT-LM     |                |  via HF Transformers        |
|                     |                |                             |
|  - 2.58 GB on disk  |                |  - ~5-6 GB VRAM (4-bit)     |
|  - 50+ tok/s        |                |  - Text + Image + Audio     |
|  - Vision + Audio   |                |  - Fine-tuned LoRA adapters |
|  - Fully offline    |                |  - Fully offline            |
|                     |                |                             |
|  Shown in VIDEO     |                |  Served via Gradio          |
|  to prove on-device |                |  (share=True for live URL)  |
+--------------------+                +-------------+---------------+
                                                    |
                                                    v
                                      +----------------------------+
                                      |   IMCI Protocol Engine      |
                                      |   (Python state machine)    |
                                      |                            |
                                      |   Danger Signs --> Breathing|
                                      |   --> Diarrhea --> Fever    |
                                      |   --> Nutrition --> [Heart] |
                                      |   --> Classify --> Treat    |
                                      |                            |
                                      |   Calls Gemma 4 at each    |
                                      |   step for perception.     |
                                      |   Applies WHO thresholds   |
                                      |   in deterministic code.   |
                                      +-------------+--------------+
                                                    |
                                                    v
                                      +----------------------------+
                                      |   OUTPUT                    |
                                      |   - MMS-TTS speaks results |
                                      |   - Gradio UI shows status |
                                      |   - Red/Yellow/Green       |
                                      +----------------------------+
```

---

## Supported Languages

| Language | Speakers | Understanding | Speech Output (MMS-TTS) |
|----------|----------|---------------|-------------------------|
| English | 1.5B | Excellent | Excellent |
| Swahili | 100M+ | Good (+ WAXAL fine-tune) | Good |
| Hindi | 600M+ | Good (base model) | Good |
| French | 300M+ | Good (base model) | Good |
| Hausa | 80M+ | Fine-tuned (WAXAL) | Good |

Covers East Africa, West Africa, South Asia, and Central/West Africa — the regions with highest child mortality.

---

## Fine-Tuning (Unsloth QLoRA)

Four LoRA adapters trained on an RTX 3060 (12GB VRAM):

| Adapter | Dataset | Purpose |
|---------|---------|---------|
| Breath sounds | ICBHI 2017 (920 recordings) | Classify wheeze, stridor, grunting, crackles |
| Skin color | Mendeley (600) + NJN (670) images | Detect jaundice, cyanosis, pallor |
| African languages | WAXAL (11,000+ hrs, 29 languages) | Improve Swahili/Hausa speech understanding |
| Heart sounds | CirCor (5,272 recordings) | Pediatric heart rate estimation (experimental) |

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| AI Model | Gemma 4 E4B (4-bit quantized via bitsandbytes) |
| Inference | HuggingFace Transformers |
| Fine-tuning | Unsloth QLoRA |
| Text-to-Speech | Meta MMS-TTS (1,100+ languages, offline) |
| UI | Gradio |
| Video processing | OpenCV |
| Audio processing | librosa, soundfile |
| On-device proof | LiteRT-LM + AI Edge Gallery (Gemma 4 E2B) |

---

## Project Structure

```
malaika/
├── config.py              # All settings in one place
├── app.py                 # Gradio entry point
├── inference.py           # Gemma 4 model — text, image, audio, video
├── tts.py                 # MMS-TTS speech output
├── imci/
│   ├── engine.py          # IMCI state machine orchestrator
│   ├── danger_signs.py    # Step 1: Danger sign assessment
│   ├── breathing.py       # Step 2: Cough/breathing
│   ├── diarrhea.py        # Step 3: Diarrhea/dehydration
│   ├── fever.py           # Step 4: Fever/malaria
│   ├── nutrition.py       # Step 5: Nutrition/wasting
│   ├── heart.py           # Step 6: Heart rate (pluggable)
│   ├── classifier.py      # Step 7: WHO classification logic
│   └── treatment.py       # Step 8: Treatment plan generation
├── prompts/               # Carefully engineered prompts per modality
├── data/                  # WHO thresholds + treatment templates (5 languages)
├── training/              # Unsloth fine-tuning scripts
├── tests/                 # 20+ clinical test scenarios
└── assets/                # Demo images, audio, video
```

---

## Running the Demo

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py

# Gradio will output a public URL for judges
```

---

## Testing

```bash
# Run all tests
python -m pytest tests/

# Run IMCI logic tests (no GPU needed)
python -m pytest tests/test_imci.py

# Run inference tests (requires GPU)
python -m pytest tests/test_inference.py
```

---

## Competition

**Hackathon**: [Gemma 4 Good Hackathon](https://www.kaggle.com/competitions/gemma-4-good-hackathon) (Kaggle + Google DeepMind)

**Track**: Health & Sciences

**Prize Target**: Main 1st ($50K) + Health & Sciences ($10K) + Unsloth ($10K) = **$70,000**

**Deadline**: May 18, 2026

---

## Why This Wins

| Dimension | Most Submissions | Malaika |
|-----------|-----------------|---------|
| Modalities | Text only | Vision + Audio + Voice + Video |
| On-device proof | "It could run on a phone" | Video of it running on a phone |
| Fine-tuning | Off-the-shelf prompting | 4 Unsloth QLoRA adapters |
| Medical validity | AI opinion | WHO IMCI protocol (100+ countries) |
| Problem scale | Vague "helps people" | 4.9 million children die/year |
| Languages | English | 5 languages across highest-mortality regions |
| Technical depth | Prompt engineering | 14+ tools, LoRA adapters, multimodal fusion, state machine |

---

## The One-Liner

**"4.9 million children die every year from treatable diseases. The WHO knows exactly how to save them. Malaika puts that knowledge in every mother's hands — in her language, through her phone, powered by Gemma 4. No internet. No training. No cost."**

---

## Team

- **Vimal Kumar** — Architecture, IMCI engine, Gradio UI, deployment, video, submission
- **Mark D. Hei Long** — Fine-tuning (Unsloth), dataset preparation, phone demo, testing

---

## License

Apache 2.0 — Because no child should die from a disease we know how to treat.

---

*Built for the Gemma 4 Good Hackathon, April–May 2026*
