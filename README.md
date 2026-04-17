# Malaika — The AI That Saves Children's Lives

> *"Malaika" means "Angel" in Swahili*

**4.9 million children died before their fifth birthday last year. Most from diseases we know how to treat.**

Malaika puts the WHO's proven [IMCI protocol](https://www.who.int/teams/maternal-newborn-child-adolescent-health-and-ageing/child-health/integrated-management-of-childhood-illness/) into every mother's hands — through her phone's camera, microphone, and voice — powered entirely by **Gemma 4**, fully offline, in her language.

This is **not a chatbot**. This is an **agentic clinical assessment tool** with 12 specialized skills — like an AED for childhood illness.

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

### Step 1 — LOOK (Gemma 4 Vision Skills)
> "Hold the phone so I can see your child's chest."

- `assess_alertness` — Camera checks if child is alert, lethargic, or unconscious
- `detect_chest_indrawing` — Detects subcostal retraction (a WHO danger sign)
- `assess_skin_color` — Jaundice, cyanosis, pallor detection
- `assess_wasting` — Visible severe malnutrition assessment
- `assess_dehydration_signs` — Sunken eyes, dry skin from face photo
- `detect_edema` — Bilateral pitting edema of feet

### Step 2 — LISTEN (Gemma 4 Vision on Spectrograms)
> Audio converted to mel-spectrograms for visual analysis by Gemma 4

- `classify_breath_sounds` — Wheezing, grunting, stridor, crackles from spectrogram
- Fine-tuned LoRA adapter: [`Vimal0703/malaika-breath-sounds-E4B-merged`](https://huggingface.co/Vimal0703/malaika-breath-sounds-E4B-merged)
- **100% crackle detection** on ICBHI dataset; 50% overall accuracy
- Novel approach: audio -> mel-spectrogram PNG -> Gemma 4 vision -> classification

### Step 3 — ASK (Voice Conversation)
> "Has your child had diarrhea? For how many days?"

- `parse_caregiver_response` — Extracts clinical intent + entities from speech
- Speaks to the caregiver **in her language** — no typing, no literacy needed
- Voice pipeline: real-time STT -> Gemma 4 reasoning -> sentence-level TTS
- Filler audio during thinking prevents dead air ("Let me check on that...")

### Step 4 — ASSESS (Agentic IMCI Protocol Engine)
> 12 skills orchestrated by BeliefState tracking

- `classify_imci_step` — Runs deterministic WHO classification (code, not LLM)
- Danger signs -> Breathing -> Diarrhea -> Fever -> Nutrition
- Per-step severity cards: RED / YELLOW / GREEN with WHO page citations
- Danger sign escalation: lethargic child -> immediate RED alert
- All classifications enforced by `imci_protocol.py` — never hallucinated

### Step 5 — ACT (Treatment Plan)
- `generate_treatment` — Step-by-step instructions in caregiver's language
- :red_circle: **URGENT** — Go to facility NOW, what to do during transport
- :yellow_circle: **Refer** — Go within 24 hours, home care while waiting
- :green_circle: **Treat at home** — ORS preparation, medication timing, danger signs to watch

---

## Agentic Architecture

Malaika is a **Guided Agent** — the WHO IMCI protocol is the plan, Gemma 4 is the perception brain, and deterministic code is the classification guard.

```
                         MALAIKA AGENT
   +---------------------------------------------------------+
   |                                                         |
   |  IMCI Protocol Guard (deterministic step ordering)      |
   |                         |                               |
   |  Agent Reasoning Core (Gemma 4 + BeliefState)           |
   |  - Confirms/uncertain/pending findings                  |
   |  - Selects which skill to invoke next                   |
   |  - Emits structured events for the UI                   |
   |         |          |          |          |              |
   |  +------+--+ +-----+---+ +---+----+ +---+----------+   |
   |  | VISION  | | AUDIO   | | SPEECH | | CLINICAL     |   |
   |  | SKILLS  | | SKILLS  | | SKILLS | | SKILLS       |   |
   |  |         | |         | |        | |              |   |
   |  |alertness| |breath   | |parse   | |classify_imci |   |
   |  |indrawing| |sounds   | |response| |generate_     |   |
   |  |dehydrate| |(spectro)| |        | |treatment     |   |
   |  |wasting  | |         | |        | |              |   |
   |  |edema    | |         | |        | |              |   |
   |  |skin_clr | |         | |        | |              |   |
   |  +---------+ +---------+ +--------+ +--------------+   |
   |                         |                               |
   |  imci_protocol.py (WHO thresholds — code, not LLM)     |
   +---------------------------------------------------------+
                         |
                         v
   +---------------------------------------------------------+
   |  VOICE UI (static/index.html)                           |
   |  - IMCI progress bar (5 steps)                          |
   |  - Skill execution cards (animated)                     |
   |  - Classification cards (RED/YELLOW/GREEN)              |
   |  - Image request cards (tappable camera)                |
   |  - Finding chips (inline badges)                        |
   |  - Danger alert banner (pulsing red)                    |
   |  - Assessment complete card (domain breakdown)          |
   |  - Audio playback queue (sentence-level TTS)            |
   +---------------------------------------------------------+
```

### Voice Pipeline (Tasha-Style)

```
Browser mic (PCM16, 16kHz)
  -> WebSocket -> Smallest AI Pulse STT -> transcript
  -> ChatEngine.process() -> {"text": str, "events": [...]}
     -> Vision skills (photo analysis)
     -> Finding extraction (Gemma 4 text parsing)
     -> WHO classification (deterministic code)
  -> Events forwarded to browser (skill cards, classifications)
  -> Sentence-level TTS (Smallest AI Waves) -> audio queue
  -> Browser speaker
```

---

## How Gemma 4 Powers Everything

This is NOT "we used Gemma 4 as a chatbot." Every core capability comes from Gemma 4:

| Gemma 4 Capability | What It Enables | Status |
|---------------------|-----------------|--------|
| Native vision on-device | 6 vision skills: alertness, indrawing, skin color, dehydration, wasting, edema | Implemented |
| Vision + fine-tuning | Breath sound classification from mel-spectrograms | [Trained (LoRA)](https://huggingface.co/Vimal0703/malaika-breath-sounds-E4B-merged) |
| Agentic tool use (1200% over Gemma 3) | 12 skills in SkillRegistry, BeliefState, structured events | Implemented |
| 140+ languages | Caregiver speaks Swahili, Hindi, Hausa — AI understands | Confirmed (Swahili tested) |
| Apache 2.0 license | Free to deploy in any country, any clinic, any phone | Yes |
| Runs in < 3GB on phone | Works on phones already in billions of pockets | E2B: 2.58GB disk |

### What is NOT Gemma 4

| Component | What It Is | Why It's Fine |
|-----------|-----------|---------------|
| IMCI Protocol (`imci_protocol.py`) | Deterministic Python code with WHO thresholds | This is a calculator, not intelligence |
| SkillRegistry (`skills.py`) | Typed tool definitions for the agent | The intelligence is Gemma 4's reasoning |
| Piper TTS | Speaks text Gemma generated aloud | Like a speaker |
| Smallest AI STT/TTS | Real-time voice I/O (optional, cloud) | Gracefully degrades to text-only offline |
| OpenCV | Extracts frames from video | Like opening a file |

---

## Fine-Tuning (Unsloth QLoRA)

Merged model: [`Vimal0703/malaika-breath-sounds-E4B-merged`](https://huggingface.co/Vimal0703/malaika-breath-sounds-E4B-merged)

| Iteration | Config | Result |
|-----------|--------|--------|
| Baseline | Zero-shot Gemma 4 E4B | 25% accuracy |
| v1 | r=8, 100 steps | 20% (too weak) |
| **v2** | **r=32, 300 steps** | **50% accuracy, 100% crackle detection** |
| Adapter size | — | 90.3 MB |

**Novel approach**: Audio -> mel-spectrogram PNG (librosa, 50-4000 Hz, 128 bands) -> Gemma 4 vision -> classification. Enables breath sound classification on a vision-only model.

Additional adapters planned:

| Adapter | Dataset | Purpose |
|---------|---------|---------|
| Skin assessment | Mendeley (600) + NJN (670) images | Jaundice, cyanosis, pallor |
| African languages | WAXAL (11,000+ hrs, 29 languages) | Swahili/Hausa speech understanding |

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| AI Model | Gemma 4 E4B (4-bit quantized via Unsloth/BitsAndBytes) |
| Agent Framework | Custom SkillRegistry + BeliefState + ChatEngine |
| Voice Pipeline | FastAPI + WebSocket + Smallest AI (STT/TTS) |
| Voice UI | Vanilla JS — orb, skill cards, classification cards, progress bar |
| Inference | HuggingFace Transformers |
| Fine-tuning | Unsloth QLoRA |
| Audio Processing | librosa (mel-spectrograms) |
| Text-to-Speech | Piper TTS (offline) / Smallest AI Waves (cloud) |
| Form UI | Gradio (alternative interface) |
| Video processing | OpenCV |
| Deployment | Colab T4 + ngrok (demo) / LiteRT-LM (phone) |
| Type checking | mypy (strict mode) |
| Linting | Ruff |
| Testing | pytest (104+ tests, 21/21 golden scenarios) |

---

## Project Structure

```
malaika/                       # Main Python package
├── skills.py                  # SkillRegistry — 12 clinical skills, BeliefState
├── chat_engine.py             # Agentic IMCI conversation — orchestrates skills
├── voice_app.py               # FastAPI server — REST + WebSocket endpoints
├── voice_session.py           # Real-time voice — sentence TTS, filler audio
├── inference.py               # Gemma 4 model — self-correcting, cached
├── imci_engine.py             # IMCI state machine (Gradio path)
├── imci_protocol.py           # WHO thresholds + classification (deterministic)
├── vision.py                  # Image/video perception via Gemma 4
├── audio.py                   # Audio perception (Whisper + spectrograms)
├── tts.py                     # Piper TTS speech output (offline)
├── spectrogram.py             # Audio -> mel-spectrogram PNG conversion
├── app.py                     # Gradio UI entry point (form-based)
├── config.py                  # Feature flags, model paths, thresholds
├── types.py                   # Shared type definitions
│
├── static/
│   └── index.html             # Voice UI — orb, skill cards, classifications
│
├── prompts/                   # Versioned, typed prompt templates (31 prompts)
│   ├── base.py                #   PromptTemplate base class
│   ├── breathing.py           #   5 breathing prompts (including spectrogram)
│   ├── danger_signs.py        #   3 danger sign prompts
│   ├── diarrhea.py            #   2 diarrhea/dehydration prompts
│   ├── fever.py               #   2 fever prompts
│   ├── nutrition.py           #   2 nutrition prompts
│   ├── heart.py               #   2 heart sounds prompts
│   ├── treatment.py           #   Treatment generation prompt
│   ├── speech.py              #   Speech understanding prompts
│   └── system.py              #   3 system personas
│
├── guards/                    # Three-layer security pipeline
│   ├── input_guard.py         #   File validation, magic bytes
│   ├── content_filter.py      #   Injection defense, PII scrubbing
│   └── output_validator.py    #   Schema validation, confidence gating
│
├── observability/             # Per-step tracing and cost tracking
│   ├── tracer.py
│   ├── cost_tracker.py
│   └── feedback.py
│
└── evaluation/                # Golden dataset evaluation
    ├── golden_scenarios.py    #   21 WHO IMCI test scenarios (100% pass)
    └── evaluator.py

notebooks/                     # Colab notebooks
├── 10_voice_agent_colab.ipynb #   PRIMARY: Voice agent on Colab T4 + ngrok
├── 09_chat_app_colab.ipynb    #   Gradio chat on Colab
└── 06_unsloth_binary_phase1.ipynb # Fine-tuning notebook

tests/                         # 104+ tests (78 protocol + 26 engine + more)
docs/                          # 6 engineering documents
adapters/                      # Fine-tuned LoRA adapter weights
configs/                       # YAML config files
```

---

## Running the Demo

### Option A: Voice Agent on Colab (Recommended)

Open [`notebooks/10_voice_agent_colab.ipynb`](notebooks/10_voice_agent_colab.ipynb) on Colab with T4 GPU:

1. Add `HF_TOKEN` to Colab Secrets (required)
2. Add `SMALLEST_API_KEY` for voice (optional — text + image work without it)
3. Add `NGROK_TOKEN` for stable tunnel (optional)
4. Run Cell 1 (installs) -> Cell 2 (model load) -> Cell 3 (launch)
5. Open the printed URL on your phone

### Option B: Gradio Form UI on Colab

Open [`notebooks/08_colab_run_app.ipynb`](notebooks/08_colab_run_app.ipynb) on Colab with T4 GPU.

### Option C: Local Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .

# Form-based UI
python -m malaika.app

# Tests (no GPU needed)
pytest tests/ -v
```

---

## Testing

```bash
# All tests (104+ passing, no GPU needed)
pytest tests/ -v

# Protocol tests only (78 tests, WHO thresholds)
pytest tests/test_imci_protocol.py -v

# Coverage report
pytest tests/ --cov=malaika --cov-report=term-missing

# Type checking
mypy malaika/ --strict

# Linting
ruff check malaika/ tests/
```

---

## Engineering Standards

| Document | What It Covers |
|----------|----------------|
| [CLAUDE.md](CLAUDE.md) | Project instructions, absolute rules, quick reference |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture, agentic voice pipeline, data flow |
| [docs/ENGINEERING_PRINCIPLES.md](docs/ENGINEERING_PRINCIPLES.md) | Core design principles, error handling, performance |
| [docs/TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md) | Testing pyramid, 21 medical scenarios, coverage targets |
| [docs/SECURITY.md](docs/SECURITY.md) | Three-layer guards, data privacy, prompt injection defense |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Code style, git workflow, dependency management |
| [docs/PROMPT_ENGINEERING.md](docs/PROMPT_ENGINEERING.md) | 31 versioned prompt templates, design rules |

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
| Architecture | Prompt wrapper | **12-skill agent** with BeliefState + structured events |
| Modalities | Text only | Vision + Audio (spectrogram) + Voice + Video |
| Classification | LLM opinion | **Deterministic WHO code** with page citations |
| On-device proof | "It could run" | Video of E2B running on phone |
| Fine-tuning | Off-the-shelf | **[LoRA on HuggingFace](https://huggingface.co/Vimal0703/malaika-breath-sounds-E4B-merged)** (100% crackle) |
| Medical validity | AI hallucination | **WHO IMCI protocol** (100+ countries, 21/21 scenarios) |
| Problem scale | Vague "helps people" | **4.9 million children** die/year |
| Languages | English | 5 languages across highest-mortality regions |
| Engineering | Single script | Guards, observability, 31 versioned prompts, 104+ tests |
| Voice UX | Text input | **Tasha-style** orb + sentence TTS + filler audio |

---

## The One-Liner

**"4.9 million children die every year from treatable diseases. The WHO knows exactly how to save them. Malaika puts that knowledge in every mother's hands — in her language, through her phone, powered by Gemma 4. No internet. No training. No cost."**

---

## Team

- **Vimal Kumar**
- **Mark D. Hei Long**

---

## License

Apache 2.0 — Because no child should die from a disease we know how to treat.

---

*Built for the Gemma 4 Good Hackathon, April-May 2026*
