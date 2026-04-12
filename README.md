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
| Piper TTS | Speaks text Gemma generated aloud | Like a speaker — the intelligence is Gemma's |
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
                                      |   - Piper TTS speaks results|
                                      |   - Gradio UI shows status |
                                      |   - Red/Yellow/Green       |
                                      +----------------------------+
```

---

## Supported Languages

| Language | Speakers | Understanding | Speech Output |
|----------|----------|---------------|---------------|
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
| AI Model | Gemma 4 E4B (4-bit quantized via BitsAndBytes) |
| Inference | HuggingFace Transformers |
| Fine-tuning | Unsloth QLoRA |
| Text-to-Speech | Piper TTS (offline) |
| UI | Gradio |
| Video processing | OpenCV |
| Type checking | mypy (strict mode) |
| Linting | Ruff |
| Testing | pytest + pytest-cov |
| On-device proof | LiteRT-LM + AI Edge Gallery (Gemma 4 E2B) |

---

## Project Structure

```
malaika/                       # Main Python package
├── inference.py               # Gemma 4 model — self-correcting, cached
├── imci_engine.py             # IMCI state machine orchestrator
├── imci_protocol.py           # WHO thresholds + classification (pure deterministic)
├── vision.py                  # Image/video perception via Gemma 4
├── audio.py                   # Audio perception via Gemma 4
├── tts.py                     # Piper TTS speech output (offline)
├── app.py                     # Gradio UI entry point
├── config.py                  # Feature flags, model paths, thresholds
├── types.py                   # Shared type definitions (dataclasses, enums)
│
├── prompts/                   # Versioned, typed prompt templates
│   ├── base.py                #   PromptTemplate base class
│   ├── breathing.py           #   Breathing rate + respiratory prompts
│   ├── danger_signs.py        #   Danger sign assessment prompts
│   ├── diarrhea.py            #   Diarrhea and dehydration prompts
│   ├── fever.py               #   Fever assessment prompts
│   ├── nutrition.py           #   Nutrition and wasting prompts
│   ├── heart.py               #   Heart sounds (MEMS) prompts
│   ├── treatment.py           #   Treatment generation prompts
│   └── speech.py              #   Speech understanding prompts
│
├── guards/                    # Three-layer security pipeline
│   ├── input_guard.py         #   File validation, size limits, format checks
│   ├── content_filter.py      #   Prompt injection defense, PII scrubbing
│   └── output_validator.py    #   Schema validation, confidence gating
│
├── observability/             # Per-step tracing and cost tracking
│   ├── tracer.py              #   IMCI step traces (input, output, latency)
│   ├── cost_tracker.py        #   Token count + inference time per call
│   └── feedback.py            #   Link corrections to traces
│
└── evaluation/                # Golden dataset evaluation
    ├── golden_scenarios.py    #   20+ WHO IMCI test scenarios
    └── evaluator.py           #   Offline accuracy reporting

tests/                         # All tests (mirrors malaika/ structure)
scripts/                       # One-off scripts (data prep, benchmarks)
adapters/                      # Fine-tuned LoRA adapter weights
configs/                       # YAML config files
data/                          # Datasets (gitignored)
docs/                          # Engineering documentation
```

---

## Engineering Standards

This project follows production-grade engineering practices:

| Document | What It Covers |
|----------|----------------|
| [CLAUDE.md](CLAUDE.md) | Project instructions, absolute rules, quick reference |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture, component boundaries, data flow |
| [docs/ENGINEERING_PRINCIPLES.md](docs/ENGINEERING_PRINCIPLES.md) | Core design principles, error handling, performance |
| [docs/TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md) | Testing pyramid, 20+ medical scenarios, coverage targets |
| [docs/SECURITY.md](docs/SECURITY.md) | Three-layer guards, data privacy, prompt injection defense |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Code style, git workflow, dependency management |
| [docs/PROMPT_ENGINEERING.md](docs/PROMPT_ENGINEERING.md) | Versioned prompt templates, design rules |

### Key Principles
- **Offline-first**: Zero network calls. Every dependency is local.
- **Gemma 4 = perception, Code = decisions**: Model observes, WHO thresholds classify.
- **Fail safe**: Uncertain AI result -> recommend referral (false positive > false negative).
- **Typed and tested**: `mypy --strict`, 80%+ coverage, 100% on protocol logic.
- **Prompts as code**: Versioned, typed, registered — never hardcoded strings.
- **Three security guards**: Input validation, content filtering, output validation on every call.
- **Self-correcting inference**: Retry with correction prompt on parse failure (max 2 retries).
- **Full observability**: Every IMCI step traced with input, output, latency, and confidence.

---

## Running the Demo

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Run the app
python -m malaika.app

# Gradio will output a public URL for judges
```

---

## Testing

```bash
# Fast: unit tests only (no GPU needed)
pytest tests/ -v -m "not gpu_required"

# Full: everything including GPU tests
pytest tests/ -v

# Coverage report
pytest tests/ --cov=malaika --cov-report=term-missing --cov-fail-under=80

# Type checking
mypy malaika/ --strict

# Linting
ruff check malaika/ tests/
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
| Engineering | Single script | Production patterns: guards, observability, versioned prompts |

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
