# Malaika — Master Execution Plan v4

> **Rule 1: MOBILE FIRST. The phone IS the product. Everything else is supplementary.**
> **Rule 2: EVERYTHING runs offline. No internet. No exceptions.**
> **Rule 3: ALL intelligence comes from Gemma 4. It IS the solution, not a tool we use.**
> **Rule 4: Every claim must be implementable. No hand-waving. If it's in the writeup, it works on the phone.**
>
> **Related files**:
> - [MALAIKA_PROPOSAL.md](./MALAIKA_PROPOSAL.md) — Idea, video script, why-it-wins
> - [DECISION_JOURNEY.md](./DECISION_JOURNEY.md) — How we arrived here
> - [RESEARCH.md](./RESEARCH.md) — Full competition research

---

## 0. Why Mobile-First Wins

Running on a GPU is not special. Any model (GPT-4, Claude, Llama) can do IMCI on a GPU.
The ONLY thing that makes this a Gemma 4 story is the phone. Gemma 4 E2B doing a real
IMCI assessment on a $150 Android phone, offline, in Swahili — no other model can do this.

**The phone is not a proof-of-concept. The phone IS the product.**

---

## 1. Hardware — What Does What

Two distinct hardware roles. The phone is PRIMARY.

| Hardware | Role | Priority |
|----------|------|----------|
| **Android phone (any 2024+, $150+)** | **PRIMARY DEMO** | Gemma 4 E2B via flutter_gemma. Full IMCI assessment: text + vision + classification + treatment. This is what judges see. |
| **RTX 3060 / Colab GPU** | TRAINING + SUPPLEMENTARY | Unsloth QLoRA fine-tuning of E4B. Kaggle notebook shows training process + before/after metrics. Wins Unsloth $10K prize. |

### Why E2B on Phone IS the Hero

| Fact | Why It Matters |
|------|---------------|
| Gemma 4 E2B runs real IMCI on a $150 phone | No other model in the world can do this |
| 2.58 GB disk, 676 MB RAM | Fits on phones already in pockets of 4 billion people |
| 50+ tok/s on-device | Fast enough for real-time conversation |
| Text + vision multimodal | Understands speech AND analyzes photos on-device |
| 140+ languages built-in | Swahili, Hindi, Hausa — no translation layer needed |
| Apache 2.0 license | Free to deploy in any country, any clinic |
| Fully offline | Works where there is no internet — which is where children die |

### Fine-Tuned E4B = Upgrade Path (Not Core Demo)

The fine-tuned E4B on GPU shows: *"When a clinic has a computer, fine-tuning improves
clinical accuracy from X% to Y%."* This is supplementary — it demonstrates the
fine-tuning capability and wins the Unsloth prize. It is NOT the main demo.

The narrative: *"Works out-of-the-box on any phone. Even better with fine-tuning where compute allows."*

### Confirmed Phone Performance (E2B)

| Device | Backend | Speed | RAM | Disk |
|--------|---------|-------|-----|------|
| Samsung S26 Ultra | GPU | 52.1 tok/s | 676 MB | 2.58 GB |
| Samsung S26 Ultra | CPU | 46.9 tok/s | 1,733 MB | 2.58 GB |
| iPhone 17 Pro | GPU | 56.5 tok/s | 1,450 MB | 2.58 GB |

Source: [LiteRT-LM E2B benchmarks on HuggingFace](https://huggingface.co/litert-community/gemma-4-E2B-it-litert-lm)

**Primary demo device**: Android (any flagship 2024+). Flutter app via flutter_gemma.
iPhone support exists in codebase but Android is the demo target.

---

## 2. How Gemma 4 IS the Solution — And Why ONLY Gemma 4

### The core question judges will ask: "Why not GPT-4 / Llama / Claude?"

Answer: **None of them can run on a phone.** That's it. That's the whole argument.

If Malaika ran on a GPU, any model could do it. Running on a $150 phone, offline, in
Swahili, with vision — that's what makes Gemma 4 the ONLY model that enables this.

### What Gemma 4 E2B does ON THE PHONE (what we demo)

| Gemma 4 Capability | What It Does in Malaika | Why Only Gemma 4 |
|--------------------|-----------------------------|-----------------|
| **Text understanding on-device** | Understands caregiver responses in natural language, extracts clinical findings | No other open model fits in 2.58GB and reasons this well |
| **Vision on-device** | Camera analyzes photos for dehydration signs, nutrition status, skin color | No other open model does multimodal vision on a phone |
| **140+ languages** | Caregiver speaks Swahili, Hindi, Hausa — AI understands and responds in their language | Built into the model, not an add-on translation layer |
| **Conversational reasoning** | Rephrases clinical questions warmly, generates caring health reports | The model IS the health worker's communication ability |
| **Apache 2.0 license** | Free to deploy in any country, any clinic, any phone | No usage restrictions, no API costs, no internet needed |
| **Runs in <3GB on phone** | Works on phones already in pockets of 4 billion people | E2B: 2.58GB disk, 676MB RAM |

### What we do NOT claim on-device (be honest)

These capabilities exist in the Python/Colab version with E4B but are NOT in the phone app:
- Breathing rate counting from video
- Breath sound classification from audio/spectrograms
- Chest indrawing detection from video
- Advanced agentic function calling with 12 skills

The phone app does: structured IMCI Q&A + photo analysis + deterministic classification
+ report generation. That is real and sufficient.

### What is NOT Gemma 4 (and why that's fine)

| Component | What It Is | Why It's Not AI |
|-----------|-----------|----------------|
| IMCI State Machine | Dart code: `if findings['has_cough'] == true: classify(...)` | This is a calculator, not intelligence. Like `2+2=4`. |
| WHO Classification | Deterministic severity rules from the IMCI protocol | Medical safety: we never let the LLM diagnose |
| Flutter UI | Displays results, captures camera input, shows progress | Like a window — what you see through it is Gemma's intelligence |

---

## 3. Architecture — Clear and Implementable

### The Complete Flow — Mobile First

```
ANDROID PHONE (PRIMARY DEMO)              GPU / COLAB (SUPPLEMENTARY)
┌─────────────────────────────┐          ┌──────────────────────────────┐
│  Flutter App + Gemma 4 E2B  │          │  Fine-tuned E4B (Unsloth)    │
│  via flutter_gemma          │          │  via Transformers            │
│                             │          │                              │
│  • 2.58 GB on disk          │          │  • Shows fine-tuning metrics │
│  • 50+ tok/s                │          │  • Before/after accuracy     │
│  • Text + Vision ✓          │          │  • Kaggle notebook           │
│  • 140+ languages ✓         │          │  • Wins Unsloth $10K prize   │
│  • Fully offline ✓          │          │                              │
│                             │          │  NOT the main demo.          │
│  THIS is the product.       │          │  Shows the upgrade path.     │
│  THIS is what judges see.   │          └──────────────────────────────┘
│                             │
│  ┌────────────────────────┐ │
│  │  IMCI Questionnaire    │ │
│  │  (Structured Q&A)      │ │
│  │                        │ │
│  │  1. Danger signs       │ │
│  │  2. Breathing          │ │
│  │  3. Diarrhea           │ │
│  │  4. Fever              │ │
│  │  5. Nutrition          │ │
│  │  + Photo analysis      │ │
│  │  + Classification      │ │
│  │  + Treatment + Report  │ │
│  └────────────────────────┘ │
│                             │
│  Gemma 4 E2B does:          │
│  • Rephrase questions warmly│
│  • Understand answers (any  │
│    language)                │
│  • Analyze photos (vision)  │
│  • Generate health report   │
│                             │
│  Deterministic code does:   │
│  • WHO IMCI classification  │
│  • Severity (🔴🟡🟢)        │
│  • Treatment selection      │
│  • Referral card generation │
└─────────────────────────────┘
```

### Skills-Based Agentic Architecture (Implemented)

The core intelligence is organized as 12 clinical **skills** in a `SkillRegistry`, orchestrated by a `ChatEngine` that drives a conversational IMCI assessment.

**`malaika/skills.py` — 12 Clinical Skills:**
| Skill | IMCI Step | Input | Purpose |
|-------|-----------|-------|---------|
| `assess_alertness` | danger_signs | image | Detect alert/lethargic/unconscious from photo |
| `assess_skin_color` | danger_signs | image | Detect jaundice, cyanosis, pallor |
| `parse_caregiver_response` | any | text | Extract clinical facts from speech/typed input |
| `detect_chest_indrawing` | breathing | image | Detect subcostal/intercostal indrawing |
| `count_breathing_rate` | breathing | video | Count breaths from 15-second chest video |
| `classify_breath_sounds` | breathing | audio/image | Classify wheeze/stridor/crackle from spectrogram |
| `assess_dehydration_signs` | diarrhea | image | Detect sunken eyes, dry appearance |
| `assess_wasting` | nutrition | image | Detect visible severe wasting |
| `detect_edema` | nutrition | image | Detect bilateral pitting edema |
| `classify_imci_step` | any | findings | Run WHO deterministic classification |
| `generate_treatment` | treatment | findings | Generate treatment plan from classifications |
| `speak_to_caregiver` | any | text | Generate empathetic voice response |

**`malaika/skills.py` — BeliefState:**
Tracks `confirmed`, `uncertain`, and `pending` findings across the assessment. Updated after each skill execution and caregiver response. The ChatEngine uses this to decide what to ask or do next.

**`malaika/chat_engine.py` — ChatEngine:**
Manages the conversational session. `ChatEngine.process()` takes caregiver input (text, image, audio) and returns structured events for the UI (transcripts, state changes, audio chunks). Maintains conversation history, belief state, and clinical findings.

**Deterministic classification** still lives in `imci_protocol.py` — WHO thresholds are code, never LLM output. The skills pattern cleanly separates Gemma 4 perception from deterministic medical logic.

### Voice Pipeline (Phase 1 prototype)

Real-time voice interaction via a single WebSocket connection (legacy path; current
demo uses the on-phone native STT/TTS in `malaika_flutter/` and the web portal at `web/`):

```
Browser mic → PCM16 audio → Whisper-small (local STT) → transcript
→ ChatEngine (Gemma 4 reasoning) → response text
→ Piper TTS (local, sentence-level) → audio chunks → Browser speaker
```

Key features (`malaika/voice_session.py`, `malaika/voice_app.py`):
- **Single WebSocket**: All communication over one connection (no HTTP polling)
- **Sentence-level TTS**: Response split at sentence boundaries, each TTS'd independently for fast first-audio
- **Filler audio**: If inference takes >1.5s, plays "Let me think about that" to prevent dead air
- **State events**: Server emits `listening`/`thinking`/`speaking` states for UI orb animation
- **Colab deployment**: `notebooks/10_voice_agent_colab.ipynb` — runs full voice pipeline on Colab GPU

### Single Inference Class (Transformers Only)

```python
# inference.py — ONE model, ONE runtime, ALL modalities
class MalaikaInference:
    """Gemma 4 E4B loaded ONCE via Transformers.
    Handles text and image through the same model.
    Audio goes through spectrogram → vision path."""
```

**One class. One model load. ~5-6GB VRAM in 4-bit.**

### Audio/Breath Sound Pipeline: Spectrogram Approach (Implemented)

Gemma 4 E4B does NOT support native audio input via Transformers. Our solution converts audio to visual spectrograms and leverages Gemma 4's working vision modality:

```
Audio file (WAV/MP3) → librosa mel-spectrogram → PNG image → Gemma 4 vision analysis
```

**`malaika/spectrogram.py` parameters** (tuned for pediatric breath sounds):
- Frequency range: 50-4000 Hz (captures grunting through high wheeze/stridor)
- 128 mel bands, 22050 Hz sample rate
- Output: 512x256 pixel PNG image

**Why spectrograms work:**
1. Spectrograms preserve ALL acoustic features (frequency, intensity, timing) as visual patterns
2. Gemma 4 vision is confirmed working (100% JSON parse rate on spectrograms)
3. Fine-tuning vision on spectrogram images is straightforward via Unsloth
4. Spectrogram generation takes ~35ms — negligible overhead

**Fine-tuning results (5 iterations on ICBHI 2017, 920 recordings):**
- Baseline (no fine-tuning): 25% accuracy (predicts all normal)
- v5 (best): 40% overall, **85% crackle detection**, 16% both-class discrimination
- Key insight: vision encoder is frozen during LoRA — language model attention adapts to interpret visual patterns
- Clear improvement trajectory validates the spectrogram approach

**Breathing rate** uses Gemma 4 video input (Approach A) or frame-by-frame vision (Approach B) as tested in Session 1.

### Heart Rate MEMS (Pluggable)

```python
# config.py
ENABLE_HEART_RATE = True  # False to disable cleanly

class HeartRateModule:
    def __init__(self, inference: MalaikaInference, enabled=True):
        self.inference = inference  # Same Gemma 4 instance — no extra model
        self.enabled = enabled

    def assess(self, audio_path: str) -> dict:
        if not self.enabled:
            return {"available": False}

        result = self.inference.analyze_audio(
            audio_path,
            "This is a phone microphone recording placed on a child's chest. "
            "Analyze for: 1) Heart rate (beats per minute), "
            "2) Any abnormal heart sounds. Report with confidence level."
        )
        return {"analysis": result, "available": True}
```

Disable: `ENABLE_HEART_RATE = False`. Zero code changes. IMCI continues without it.

---

## 4. Fine-Tuning Strategy — Supplementary, Not Core

### Role of Fine-Tuning

Fine-tuning is NOT what makes Malaika work. The phone app runs base E2B and delivers
a complete IMCI assessment. Fine-tuning shows:
1. Domain adaptation improves accuracy (before/after metrics)
2. Unsloth makes fine-tuning accessible (wins $10K Unsloth prize)
3. The upgrade path for clinics with compute

### What Gets Fine-Tuned

| What | Base Model | Method | Data | Purpose |
|------|-----------|--------|------|---------|
| Breath sound classification | Gemma 4 E4B | Unsloth QLoRA 4-bit | ICBHI 2017 (920 recordings) | Show fine-tuning improves clinical perception |
| Skin color (jaundice/cyanosis) | Gemma 4 E4B | Unsloth QLoRA 4-bit | Mendeley (600) + NJN (670) images | Vision fine-tuning for clinical domain |

### How Fine-Tuning Is Shown to Judges

```
Kaggle Notebook (PUBLIC)
    │
    │  1. Load Gemma 4 E4B in 4-bit via Unsloth
    │  2. Train LoRA adapter on clinical data
    │  3. Show before/after accuracy metrics
    │  4. Export adapter weights
    │
    ▼
Writeup + Video
    │
    │  "Base model: X% accuracy on breath sounds"
    │  "After Unsloth fine-tuning: Y% accuracy"
    │  "The phone runs base E2B. Clinics can deploy
    │   fine-tuned E4B for higher accuracy."
    │
    ▼
Judges see: fine-tuning capability + honest deployment story
```

**Important**: The phone runs BASE Gemma 4 E2B. The fine-tuned E4B is demonstrated
in a Kaggle notebook with metrics. This is honest — the phone works out-of-the-box,
fine-tuning is the upgrade path.

### Unsloth Training Code (Confirmed for RTX 3060 12GB)

```python
from unsloth import FastModel

# Step 1: Load in 4-bit (fits 12GB VRAM)
model, tokenizer = FastModel.from_pretrained(
    model_name="unsloth/gemma-4-E4B-it",
    max_seq_length=8192,
    load_in_4bit=True,
)

# Step 2: Add LoRA adapter
model = FastModel.get_peft_model(
    model,
    finetune_vision_layers=True,   # For jaundice adapter
    finetune_language_layers=True,
    finetune_attention_modules=True,
    finetune_mlp_modules=True,
    r=8, lora_alpha=8, lora_dropout=0, bias="none",
)

# Step 3: Train
from trl import SFTTrainer, SFTConfig
trainer = SFTTrainer(
    model=model, tokenizer=tokenizer,
    train_dataset=formatted_dataset,  # 150-300 instruction pairs
    args=SFTConfig(
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        max_steps=60,
        learning_rate=2e-4,
        optim="adamw_8bit",
    ),
)
trainer.train()

# Step 4: Save merged model
model.save_pretrained_merged("malaika-e4b-finetuned", tokenizer)
```

**Resolved**: Native audio fine-tuning is not possible — Gemma 4 E4B does not support audio input via Transformers. Solution: **spectrogram approach** — convert audio to mel-spectrogram PNG images and fine-tune vision+language layers. 5 iterations completed (see Session Log), best result v5 = 40% accuracy on full ICBHI test set, 85% crackle detection. Vision encoder is frozen during LoRA; language model attention learns to interpret spectrogram visual patterns.

---

## 5. Datasets — All Confirmed Available

| # | Dataset | Size | License | Download | Purpose |
|---|---------|------|---------|----------|---------|
| 1 | **ICBHI 2017** | 920 recordings, 3.96 GB | Research use | [Kaggle](https://www.kaggle.com/datasets/vbookshelf/respiratory-sound-database) | Fine-tune breath sound classification |
| 2 | **WAXAL** | 11,000+ hrs, 29 African languages | CC-BY-4.0 | [HuggingFace](https://huggingface.co/datasets/google/WaxalNLP) | Fine-tune African language speech |
| 3 | **Neonatal Jaundice (Mendeley)** | 600 images + bilirubin levels | CC-BY-4.0 | [Mendeley](https://data.mendeley.com/datasets/yfsz6c36vc/1) | Fine-tune jaundice detection |
| 4 | **Neonatal Jaundice (NJN)** | 670 images | CC-BY-4.0 | [Zenodo](https://zenodo.org/records/7825810) | Supplementary jaundice data |
| 5 | **Pediatric Breathing Videos** | 332 videos (children 0-59mo) | Open access | [BMC 2026](https://link.springer.com/article/10.1186/s13104-026-07677-x) | Validate breathing rate from video |
| 6 | **CirCor Heart Sounds** | 5,272 pediatric recordings | ODC-By 1.0 | [PhysioNet](https://physionet.org/content/circor-heart-sound/1.0.3/) | Fine-tune MEMS heart module |
| 7 | **WHO IMCI Protocol** | Clinical decision tree | CC-BY-IGO 3.0 | [WHO EmCare GitHub](https://github.com/WorldHealthOrganization/smart-emcare) | Encode state machine |

---

## 6. IMCI Protocol Engine

The state machine is deterministic code. Gemma 4 is called at each step for perception and reasoning. WHO thresholds are hardcoded.

```
START → DANGER SIGNS → BREATHING → DIARRHEA → FEVER → NUTRITION → [HEART MEMS] → CLASSIFY → TREAT
```

### At Each Step: What Gemma 4 Does vs. What Code Does

| Step | Gemma 4 Does (AI) | Code Does (Logic) |
|------|-------------------|-------------------|
| **Danger signs** | Understands caregiver's voice in any language, assesses child's alertness from camera | Checks: any danger sign present? → 🔴 urgent |
| **Breathing** | Counts breathing rate from video, classifies breath sounds from mic audio, detects chest indrawing from image | Compares rate to WHO thresholds (≥50 for 2-11mo, ≥40 for 12-59mo) |
| **Diarrhea** | Understands duration/blood reports via voice, guides and observes skin pinch test via camera | Applies WHO dehydration classification matrix |
| **Fever** | Conversational assessment via voice, contextual reasoning about malaria risk | Applies WHO fever classification rules |
| **Nutrition** | Visual wasting assessment from camera, guides MUAC measurement | Compares MUAC to WHO thresholds (<115mm severe) |
| **Heart (MEMS)** | Analyzes heart sounds from chest mic recording | Estimates BPM, flags abnormalities |
| **Treatment** | Generates clear step-by-step instructions in caregiver's local language | Selects treatment template based on classification |

---

## 7. Sprint Plan — 36 Days

```
PHASE 1 (Apr 12-18): Foundation — COMPLETED ✓ (227 tests, 21/21 golden, voice pipeline, skills architecture)
PHASE 2 (Apr 19-25): Core IMCI — Full assessment working with vision + audio
PHASE 3 (Apr 26-May 2): Multilingual + Polish — Multiple languages, stability
PHASE 4 (May 3-9): Fine-tuning + MEMS + Deploy — Adapters deployed, MEMS GO/NO-GO, live URL
PHASE 5 (May 10-18): Video + Writeup + Submit
```

### PHASE 1: Foundation (April 12-18) — COMPLETED

| Day | Tasks | Status |
|-----|-------|--------|
| 1 | Git repo, project structure, engineering docs | DONE — CLAUDE.md + 7 engineering docs |
| 2 | Load E4B in 4-bit, test image + audio + video | DONE — image works, native audio NOT supported (Whisper fallback) |
| 3 | Build Gradio UI, explore ICBHI, prepare training data | DONE — Gradio app + ICBHI spectrogram pipeline |
| 4 | Connect Gemma 4 vision to UI, spectrogram pipeline, real data testing | DONE — 227 tests, spectrogram baseline 25% |
| 4+ | Fine-tuning iterations v1-v5, Colab deployment | DONE — 5 LoRA iterations, best v5 = 40% accuracy |
| 5 | Skills-based agentic architecture, ChatEngine | DONE — 12 skills in SkillRegistry, BeliefState |
| 5+ | Voice pipeline (WebSocket + sentence TTS + filler audio, local STT/TTS) | DONE — real-time voice on Colab (Phase 1 prototype) |
| 7 | **MILESTONE**: Full voice assessment pipeline working | DONE |

**Phase 1 Accomplishments:**
- 227 tests passing (78 protocol + 26 engine + 19 vision + 25 audio + 20 prompts + 15 TTS + 8 spectrogram + more)
- 21/21 golden scenarios at 100% accuracy (deterministic WHO classification)
- 5/5 JSON reliability (100%) after thinking-mode suppression fix
- Skills-based agentic architecture with 12 clinical skills
- Voice pipeline: WebSocket + Whisper-small (local STT) + Piper (local TTS) + sentence-level streaming + filler audio
- Colab deployment working (`notebooks/10_voice_agent_colab.ipynb`)
- Fine-tuning: 5 iterations (v1-v5), best v5 = 40% overall, 85% crackle detection
- Spectrogram approach validated: audio → mel-spectrogram PNG → Gemma 4 vision

**Day 2 Feasibility Test Results (COMPLETED):**
- [x] Can Gemma 4 E4B via Transformers analyze an image? **YES** — valid JSON, describes images accurately
- [x] Can Gemma 4 E4B via Transformers understand speech audio? **NO** — native audio not supported, Whisper fallback implemented
- [x] Can Gemma 4 E4B count breathing rate from a video clip? Untested (video approach deferred)
- [x] Can Gemma 4 E4B classify breath sounds from ICBHI audio samples? **YES via spectrograms** — 25% baseline, 40% after fine-tuning
- [x] How much VRAM does E4B 4-bit use via Transformers? **~5-6GB confirmed on T4**
- [x] What is the latency for image analysis? Audio analysis? **Vision: 28s, text: 42s, spectrogram gen: 35ms, 5.9-7.4 tok/s**

### PHASE 2: Core IMCI (April 19-25)

| Day | Tasks |
|-----|-------|
| 8 | Complete IMCI state machine (all states + transitions). Complete breath sound training, evaluate accuracy. |
| 9 | Integrate breathing assessment (video or image-based, per Day 2 results). Begin jaundice LoRA training. |
| 10 | Integrate chest indrawing + skin color detection. Integrate trained breath sound adapter. |
| 11 | Build dehydration + fever assessment flows. Complete jaundice training, integrate. |
| 12 | Build nutrition assessment flow. Test all adapters end-to-end. |
| 13 | Build classification aggregator + treatment generator. Accuracy metrics. |
| 14 | **MILESTONE**: Complete IMCI assessment end-to-end. All core adapters trained and tested. |

### PHASE 3: Multilingual + Polish (April 26 - May 2)

| Day | Tasks |
|-----|-------|
| 15-16 | Test multilingual responses (Swahili, Hindi, Hausa). Train WAXAL language adapter. |
| 17-18 | Build assessment history (local storage), UI improvements. Deploy language adapter. |
| 19-20 | Stress test 20+ scenarios, fix bugs across all modules. |
| 21 | **MILESTONE**: Multilingual assessment working, stable. All adapters deployed. |

### PHASE 4: MEMS + Deploy (May 3-9)

| Day | Tasks |
|-----|-------|
| 22-23 | UI polish, mobile-responsive. Train heart sound adapter (CirCor), test MEMS. |
| 24 | **MEMS GO/NO-GO** (May 6). |
| 25-26 | Set up live demo (Gradio share=True or cloud GPU). If MEMS GO: integrate. If NO-GO: disable. |
| 27 | Test live demo URL end-to-end. Set up AI Edge Gallery on phone with E2B. |
| 28 | **MILESTONE**: Live demo URL working + phone demo recorded. |

### PHASE 5: Video + Submit (May 10-18)

| Day | Tasks |
|-----|-------|
| 29-30 | Finalize video script, record demo footage, record phone demo, source B-roll. |
| 31-32 | Video editing, narration, music. |
| 33-34 | Video polish, upload YouTube. GitHub cleanup, README. |
| 35 | Kaggle writeup (1,500 words). |
| 36 | Final review all materials. |
| 37 (May 18) | **SUBMIT**. |

---

## 8. How We Differentiate from Every Other Submission

### What most teams will do
- Use Gemma 4 as a text chatbot ("ask health questions")
- Run it on a laptop or Colab, claim it "could" run on a phone
- Use off-the-shelf model, no fine-tuning
- Single modality (text only)
- Generic health/education/agriculture chatbot

### What we do differently

| Dimension | Most Teams | Malaika |
|-----------|-----------|---------|
| **Runs on a phone** | "It could run on a phone" | **Android app running live** — complete IMCI assessment on-device |
| **Offline** | Needs internet / API calls | **Zero internet.** Everything on-device. Works where children die. |
| **Real medical protocol** | AI opinion / chatbot advice | **WHO IMCI protocol** — validated in 100+ countries, deterministic classification |
| **Vision on-device** | Text only | Camera analyzes photos for dehydration, nutrition, skin color — on the phone |
| **Multilingual** | English only | 140+ languages. Demo in English + Swahili + Hindi |
| **Medical safety** | LLM diagnoses | **LLM perceives, code classifies.** WHO thresholds are deterministic, never AI output |
| **Fine-tuning** | Off-the-shelf prompting | Unsloth QLoRA on clinical data. Before/after metrics in notebook |
| **Problem scale** | Vague "helps people" | 4.9 million children die/year (WHO, March 2026) |
| **Not a chatbot** | Q&A with an LLM | Structured clinical assessment following a published protocol |

### Why "only Gemma 4" — the question judges will ask

> "Why not use GPT-4 or Claude for this?"
>
> Because GPT-4 needs internet. Claude needs an API key. Llama doesn't fit on a phone
> with vision. Gemma 4 E2B runs a complete multimodal medical assessment in 2.58GB,
> offline, in 140+ languages. Where this matters — rural clinics with no internet —
> no other model can do this.

### Competition Alignment Scorecard

| Judging Criterion | Weight | How We Score Maximum |
|-------------------|--------|---------------------|
| **Innovation (30%)** | Novel approach | Only submission with a real medical protocol as structured assessment on a phone |
| **Impact (30%)** | Scale of problem | 4.9M children/year. WHO IMCI. Offline where it matters most. |
| **Technical Execution (25%)** | Quality of implementation | Flutter app, deterministic classification, vision on-device, fine-tuning with Unsloth |
| **Accessibility (15%)** | Resource-constrained | $150 phone, 2.58GB, no internet, any language |

---

## 9. Testing Strategy

### Day 2 Feasibility Tests (MUST PASS)

| Test | Pass Criteria | If Fails |
|------|--------------|----------|
| E4B 4-bit loads via Transformers | Uses <8GB VRAM | Use E2B instead |
| Image analysis (skin photo) | Identifies jaundice/cyanosis | Increase prompt detail, fine-tune priority |
| Audio speech understanding | Understands English speech from WAV | Test different audio formats/durations |
| Audio breath classification | Distinguishes wheeze from normal (base model) | Fine-tuning becomes higher priority |
| Video breathing rate | Counts chest rises from 15s video | Fall back to frame-by-frame approach |

### Test Scenarios (20+)

| # | Scenario | Expected | Key Gemma 4 Feature Tested |
|---|----------|----------|---------------------------|
| 1 | Fast breathing, no other signs | 🟡 Pneumonia | Video analysis (breathing rate) |
| 2 | Chest indrawing + stridor | 🔴 Severe pneumonia | Vision + audio |
| 3 | Watery diarrhea, slow skin pinch | 🟡 Some dehydration | Vision (skin pinch) + voice |
| 4 | Unable to drink, lethargic | 🔴 Urgent referral | Voice + vision (alertness) |
| 5 | Fever 3 days, malaria area | 🟡 Malaria | Voice (reasoning) |
| 6 | Cough, normal breathing rate | 🟢 Cough/cold | Video (rate counting) |
| 7 | Vomiting everything | 🔴 Urgent referral | Voice understanding |
| 8 | Jaundiced skin | 🟡 Jaundice | Vision (fine-tuned) |
| 9 | Severe wasting visible | 🔴 Severe malnutrition | Vision |
| 10 | Wheezing, no fast breathing | 🟢 Wheeze, no pneumonia | Audio (fine-tuned) |
| 11-20 | Combinations, edge cases, multilingual | Various | All modalities |

### Accuracy Targets

| Component | Target | How Measured |
|-----------|--------|-------------|
| Breathing rate (video) | ±5 breaths/min | Compare vs expert count |
| Breath sounds | >80% accuracy | ICBHI test split |
| Jaundice detection | >75% sensitivity | Mendeley test split |
| Speech understanding (English) | >90% | Manual evaluation |
| Speech understanding (Swahili) | >70% | Manual evaluation |
| IMCI classification | 100% on test scenarios | Deterministic code |
| Heart rate MEMS (if GO) | ±10 BPM | CirCor annotations |

---

## 10. Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| E4B 4-bit too large for demo machine | HIGH | Use E2B for demo (still multimodal, still impressive) |
| Gemma 4 can't count breathing rate from video | HIGH | Frame-by-frame vision analysis, or OpenCV motion + Gemma 4 for other visual signs |
| Audio fine-tuning not supported by Unsloth | Medium | Use strong prompting + few-shot examples in context for audio tasks |
| Base model breath sound classification too poor | Medium | Fine-tuning is Plan A. If fine-tuning fails, use detailed prompts describing what wheeze/stridor sounds like |
| MEMS heart rate doesn't work | Low | Pluggable — disable, IMCI continues with visual circulation assessment |
| Audio latency too slow (>30s per clip) | Medium | Shorten clips to 10-15s. Frame as "Malaika is listening carefully..." |
| Judges question medical validity | Medium | "WHO IMCI decision SUPPORT, not diagnosis. Protocol validated across 100+ countries." |
| Scope creep | HIGH | Core IMCI first. MEMS second. NO new features after Phase 4. |
| Model crashes during live demo | HIGH | Pre-recorded backup video. Test stability extensively in Phase 4. |

---

## 11. Submission Checklist

### Mandatory (May 18)

- [ ] **Kaggle Writeup** — 1,500 words max, Track: Health & Sciences
- [ ] **YouTube Video** — 3 min, public. Android app demo is the hero.
- [ ] **Public GitHub Repo** — documented, reproducible, no secrets
- [ ] **Android App APK / Demo** — the primary demo artifact
- [ ] **Media Gallery** — cover image, screenshots of phone app, architecture diagram
- [ ] **Writeup SUBMITTED** (not just draft)

### Winning Edge

- [ ] Android app running complete IMCI assessment end-to-end on-device
- [ ] Multi-language demo: English + Swahili (+ Hindi if possible)
- [ ] Photo analysis working on-device (dehydration, nutrition)
- [ ] Referral card generation after assessment
- [ ] Kaggle notebook showing Unsloth fine-tuning + before/after metrics
- [ ] 20+ validated test scenarios with accuracy metrics in writeup

---

## 12. Definition of Done

### Must Ship (Minimum Viable)
1. Android app running complete IMCI assessment on-device with Gemma 4 E2B
2. All 5 clinical steps: danger signs → breathing → diarrhea → fever → nutrition
3. Photo analysis on-device (dehydration, nutrition signs)
4. Deterministic WHO classification (red/yellow/green)
5. Treatment summary + referral card
6. English + Swahili working
7. ALL offline, ALL Gemma 4, ALL on phone
8. Video, repo, demo, writeup submitted

### Must Ship to Win First Prize
All above PLUS:
1. Polished Flutter UI that looks like a real product (not a hackathon prototype)
2. Multi-language demo in video (EN + SW + HI)
3. Kaggle notebook with Unsloth fine-tuning + before/after accuracy metrics
4. Professional video: emotional story + live phone demo
5. 20+ validated test scenarios with accuracy data in writeup
6. Referral card that a mother can show at a clinic

---

## 13. Work Streams

All work is pooled — any task can be picked up by any team member. Priority order:

### Stream A: Core Application (Critical Path)
- Architecture, project setup, engineering docs
- IMCI protocol engine (state machine + WHO thresholds)
- Gemma 4 integration (Transformers inference)
- Perception modules (vision, audio, video analysis)
- Prompt engineering (versioned PromptTemplates)
- Gradio UI

### Stream B: Fine-Tuning (Parallel)
- Dataset preparation and formatting (ICBHI, jaundice, WAXAL, CirCor)
- Unsloth QLoRA training on RTX 3060
- Adapter evaluation and integration
- Accuracy benchmarking

### Stream C: Deployment & Polish
- Live demo deployment (Gradio share=True or cloud GPU)
- Phone demo setup (AI Edge Gallery + E2B)
- Multilingual testing
- Stress testing 20+ scenarios

### Stream D: Submission
- Video production (script, footage, editing)
- Kaggle writeup (1,500 words)
- GitHub repo cleanup, README
- Final submission

---

*Plan v6: April 18, 2026*
*Changes from v5: MOBILE-FIRST pivot. Phone is the primary demo, not GPU. Android app
with Gemma 4 E2B is the product. GPU/fine-tuning is supplementary (Unsloth prize +
upgrade path story). Removed claims about on-device capabilities we don't have (breath
counting from video, spectrogram analysis on phone). Honest about what E2B does on-device
vs. what E4B does on GPU.*
*Deadline: May 18, 2026 (30 days remaining)*
