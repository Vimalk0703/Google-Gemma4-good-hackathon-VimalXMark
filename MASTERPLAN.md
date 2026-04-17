# Malaika — Master Execution Plan v3

> **Rule 1: EVERYTHING runs on the edge. No internet. No exceptions.**
> **Rule 2: ALL intelligence comes from Gemma 4. It IS the solution, not a tool we use.**
> **Rule 3: Every claim must be implementable. No hand-waving.**
>
> **Related files**:
> - [MALAIKA_PROPOSAL.md](./MALAIKA_PROPOSAL.md) — Idea, video script, why-it-wins
> - [DECISION_JOURNEY.md](./DECISION_JOURNEY.md) — How we arrived here
> - [RESEARCH.md](./RESEARCH.md) — Full competition research

---

## 1. Hardware — What Does What

Three distinct hardware roles. Do NOT confuse them.

| Hardware | Role | What Runs On It |
|----------|------|----------------|
| **Mark's RTX 3060 (12GB)** | TRAINING ONLY | Unsloth QLoRA fine-tuning of Gemma 4 E4B. NOT used for demo inference. |
| **Demo machine (laptop/desktop with GPU)** | LIVE DEMO | Fine-tuned Gemma 4 E4B via Transformers. Serves the Gradio web app judges interact with. |
| **Android phone (flagship 2024+)** | VIDEO PROOF | Gemma 4 E2B via LiteRT-LM / AI Edge Gallery. Proves "it runs on a phone" in our 3-min video. |

### Why Two Models (E2B + E4B)

| Model | Where | Why |
|-------|-------|-----|
| **E4B** (4.5B active) | Demo machine (Transformers) | Better reasoning (+12 pts avg), better vision, better for medical assessment. Judges interact with this. |
| **E2B** (2.3B active) | Phone (LiteRT-LM) | Proven on-phone: 50+ tok/s, 2.58GB, vision + audio + function calling. Shown in video to prove on-device. |

Both are Gemma 4. Both are offline. Both are multimodal. The live demo uses the stronger model for accuracy. The video proves it also runs on a $200 phone. This is honest and impressive.

### Confirmed Phone Performance (E2B via LiteRT-LM)

| Device | Backend | Speed | RAM | Disk |
|--------|---------|-------|-----|------|
| Samsung S26 Ultra | GPU | 52.1 tok/s | 676 MB | 2.58 GB |
| iPhone 17 Pro | GPU | 56.5 tok/s | 1,450 MB | 2.58 GB |
| Samsung S26 Ultra | CPU | 46.9 tok/s | 1,733 MB | 2.58 GB |

Source: [LiteRT-LM E2B benchmarks on HuggingFace](https://huggingface.co/litert-community/gemma-4-E2B-it-litert-lm)

---

## 2. How Gemma 4 IS the Solution

### What Gemma 4 does that makes Malaika possible

This is NOT "we used Gemma 4 as a chatbot." Gemma 4 enables capabilities that **did not exist before** on a phone:

| Gemma 4 Capability | What It Enables in Malaika | Why Only Gemma 4 |
|--------------------|-----------------------------|-----------------|
| **Native vision on-device** | Camera sees chest indrawing, jaundice, wasting, dehydration signs | No other open model does multimodal vision on a phone at this quality |
| **Native audio on-device** | Mic hears breath sounds (wheezing, stridor, grunting), understands speech in any language | E2B/E4B have built-in audio encoder — not a separate pipeline |
| **Native function calling** | IMCI protocol steps as tool calls — model decides which assessment to run next | 1200% improvement over Gemma 3 in agentic tool use |
| **140+ languages** | Caregiver speaks Swahili, Hausa, Hindi — AI understands and responds | Built into the model, not an add-on translation layer |
| **Apache 2.0 license** | Free to deploy in any country, any clinic, any phone | Previous Gemma versions had restrictive license |
| **Runs in <3GB on phone** | Works on phones already in pockets of billions | E2B Q4: 2.58GB disk, 676MB RAM on GPU |

### What is NOT Gemma 4 (and why that's fine)

| Component | What It Is | Why It's Not AI |
|-----------|-----------|----------------|
| IMCI State Machine | Python code: `if breathing_rate > 50: classify = "pneumonia"` | This is a calculator, not intelligence. Like `2+2=4`. |
| TTS (Piper) | Plays audio of text Gemma generated | Like a speaker playing music. The intelligence is in the composition (Gemma). |
| OpenCV frame extraction | Pulls frames from video to feed to Gemma 4 | Like opening a file to read it. The reading (analysis) is Gemma. |
| Gradio UI | Displays results, captures camera/mic input | Like a window — what you see through it is Gemma's intelligence. |

---

## 3. Architecture — Clear and Implementable

### The Complete Flow

```
PHONE (Video proof)                    DEMO MACHINE (Live demo)
┌────────────────────┐                ┌─────────────────────────────┐
│  Gemma 4 E2B       │                │  Gemma 4 E4B (fine-tuned)   │
│  via LiteRT-LM     │                │  via Transformers           │
│                    │                │                             │
│  • 2.58 GB on disk │                │  • ~5-6 GB Q4 in VRAM      │
│  • 50+ tok/s       │                │  • All modalities:          │
│  • Vision ✓        │                │    text + image + audio     │
│  • Audio ✓         │                │  • Fine-tuned LoRA adapters │
│  • Function call ✓ │                │    for medical domain       │
│  • Offline ✓       │                │  • Offline ✓                │
│                    │                │                             │
│  Shown in VIDEO    │                │  Served via Gradio          │
│  to prove on-device│                │  (share=True for public URL)│
└────────────────────┘                └──────────────┬──────────────┘
                                                     │
                                                     ▼
                                      ┌──────────────────────────────┐
                                      │  IMCI Protocol Engine         │
                                      │  (Python state machine)       │
                                      │                              │
                                      │  Orchestrates assessment:     │
                                      │  1. Danger signs (voice+vision│
                                      │  2. Breathing (vision+audio) │
                                      │  3. Diarrhea (voice+vision)  │
                                      │  4. Fever (voice)            │
                                      │  5. Nutrition (vision+voice) │
                                      │  6. Heart rate [MEMS,optional│
                                      │  7. Classification+Treatment │
                                      │                              │
                                      │  At each step, calls Gemma 4 │
                                      │  for perception + reasoning.  │
                                      │  Applies WHO thresholds in    │
                                      │  deterministic code.          │
                                      └──────────────┬──────────────┘
                                                     │
                                                     ▼
                                      ┌──────────────────────────────┐
                                      │  OUTPUT                       │
                                      │  • Piper TTS speaks results  │
                                      │  • Gradio UI shows assessment│
                                      │  • 🔴🟡🟢 classification      │
                                      └──────────────────────────────┘
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

### Voice Pipeline (Tasha-Style Architecture)

Real-time voice interaction via a single WebSocket connection:

```
Browser mic → PCM16 audio → Smallest AI STT → transcript
→ ChatEngine (Gemma 4 reasoning) → response text
→ Smallest AI TTS (sentence-level) → audio chunks → Browser speaker
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

## 4. Fine-Tuning Strategy

### What Gets Fine-Tuned, On What, How

| What | Hardware | Base Model | Method | Data | Time |
|------|----------|-----------|--------|------|------|
| Breath sound classification | Mark's RTX 3060 | Gemma 4 E4B | Unsloth QLoRA 4-bit | ICBHI 2017 (920 recordings) | ~3 hrs |
| Skin color (jaundice/cyanosis) | Mark's RTX 3060 | Gemma 4 E4B | Unsloth QLoRA 4-bit | Mendeley (600) + NJN (670) images | ~3 hrs |
| African language speech | Mark's RTX 3060 | Gemma 4 E4B | Unsloth QLoRA 4-bit | WAXAL subset (Swahili, Hausa, Yoruba) | ~3 hrs |
| Heart sounds (MEMS) | Mark's RTX 3060 | Gemma 4 E4B | Unsloth QLoRA 4-bit | CirCor (5,272 recordings) | ~3 hrs |

### Fine-Tuning → Deployment Flow

```
Mark's RTX 3060 (TRAINING)
    │
    │  1. Load Gemma 4 E4B in 4-bit via Unsloth
    │  2. Train LoRA adapter (~150-300 instruction pairs)
    │  3. Export merged model or adapter weights
    │
    ▼
Exported Model / Adapters
    │
    │  4. Transfer to demo machine
    │  5. Load fine-tuned model via Transformers
    │
    ▼
Demo Machine (INFERENCE)
    │
    │  6. Serve via Gradio (share=True for public URL)
    │  7. Judges interact with fine-tuned model
    │
    ▼
Phone (VIDEO PROOF)
    │
    │  8. AI Edge Gallery with BASE E2B (not fine-tuned)
    │  9. Proves on-device capability for the video
    │
    ▼
Judges see: fine-tuned quality in live demo + on-device proof in video
```

**Note**: The phone runs BASE Gemma 4 E2B (fine-tuned models can't easily load into AI Edge Gallery). The live demo runs FINE-TUNED Gemma 4 E4B. This is honest — we show both, explain the difference in the writeup, and demonstrate that the architecture works end-to-end on-device.

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
| 5+ | Voice pipeline (Tasha-style WebSocket + sentence TTS + filler audio) | DONE — real-time voice on Colab |
| 7 | **MILESTONE**: Full voice assessment pipeline working | DONE |

**Phase 1 Accomplishments:**
- 227 tests passing (78 protocol + 26 engine + 19 vision + 25 audio + 20 prompts + 15 TTS + 8 spectrogram + more)
- 21/21 golden scenarios at 100% accuracy (deterministic WHO classification)
- 5/5 JSON reliability (100%) after thinking-mode suppression fix
- Skills-based agentic architecture with 12 clinical skills
- Voice pipeline: WebSocket + Smallest AI STT/TTS + sentence-level streaming + filler audio
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
- Run it on a laptop, claim it "could" run on a phone
- Use off-the-shelf model, no fine-tuning
- Single modality (text only)
- Generic health/education/agriculture chatbot

### What we do differently

| Dimension | Most Teams | Malaika |
|-----------|-----------|---------|
| **Modalities** | Text only | Vision + Audio + Voice + Video — ALL through Gemma 4 |
| **On-device proof** | "It could run on a phone" | VIDEO of it running on a phone (AI Edge Gallery + E2B) |
| **Fine-tuning** | Off-the-shelf prompting | Unsloth QLoRA: breath sounds, skin color, African languages |
| **Medical validity** | AI opinion | WHO IMCI protocol — validated across 100+ countries |
| **Problem scale** | Vague "helps people" | 4.9 million children die/year (WHO, March 2026) |
| **Agentic** | Simple Q&A | Multi-step protocol with function calling across modalities |
| **Languages** | English | 140+ languages, fine-tuned for African languages via WAXAL |
| **Technical depth** | Prompt engineering | 14+ tools, LoRA adapters, multimodal fusion, state machine |
| **Emotional video** | Screen recording | Narrative: mother saving child at 2am, no internet, no clinic |

### Competition Alignment Scorecard

| Judging Criterion | Points | How We Score Maximum |
|-------------------|--------|---------------------|
| **Impact & Vision (40 pts)** | 4.9M children/year. WHO data from 3 weeks ago. Video shows specific human story. | 38-40 |
| **Video Pitch (30 pts)** | Emotional narrative, live demo, on-phone proof, compelling music/pacing | 26-30 |
| **Technical Depth (30 pts)** | 4 LoRA fine-tuned adapters, all Gemma 4 modalities used, WHO protocol engine, on-device deployment | 26-30 |

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
- [ ] **YouTube Video** — 3 min, public, emotional narrative + technical demo
- [ ] **Public GitHub Repo** — documented, reproducible, no secrets
- [ ] **Live Demo URL** — Gradio (share=True), no login, mobile-friendly
- [ ] **Media Gallery** — cover image, screenshots, architecture diagram
- [ ] **Writeup SUBMITTED** (not just draft)

### Bonus (Winning Edge)

- [ ] Fine-tuned LoRA adapters (Unsloth) → targets Unsloth $10K prize
- [ ] Heart rate MEMS module working
- [ ] 3+ languages demonstrated
- [ ] Phone demo in video (AI Edge Gallery + E2B) → proves on-device
- [ ] 20+ validated test scenarios with accuracy metrics
- [ ] Kaggle notebook showing fine-tuning process

---

## 12. Definition of Done

### Must Ship (Minimum Viable)
1. Full IMCI: danger signs → breathing → diarrhea → fever → nutrition → classify → treat
2. Gemma 4 vision: chest indrawing + skin color + wasting
3. Gemma 4 audio: breath sounds + speech understanding
4. Gemma 4 language: treatment in English + 1 other language
5. TTS spoken output (Piper)
6. ALL offline, ALL Gemma 4
7. Video, repo, demo, writeup submitted

### Must Ship to Win
All above PLUS:
1. Fine-tuned LoRA adapters deployed (Unsloth)
2. 3+ languages working (including African via WAXAL)
3. Phone demo in video (E2B on AI Edge Gallery)
4. Professional video with emotional story
5. Heart rate MEMS working (or cleanly disabled with explanation)
6. 20+ test scenarios with accuracy data in writeup

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

*Plan v5: April 16, 2026*
*Changes from v4: Phase 1 completed — skills-based agent architecture, voice pipeline, spectrogram approach, 5 fine-tuning iterations. Updated architecture section with implemented patterns.*
*Deadline: May 18, 2026 (32 days remaining)*
*Team: Vimal Kumar + Mark D. Hei Long*
