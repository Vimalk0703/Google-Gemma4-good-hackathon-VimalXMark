# Malaika — System Architecture

> Single source of truth for system design. All implementation must conform to this document.

---

## 1. System Overview

Malaika is an offline-first, multimodal child health assessment system built on Gemma 4. It implements the WHO IMCI (Integrated Management of Childhood Illness) protocol as a deterministic state machine, using Gemma 4 for all perception (vision, audio, language understanding) and code for all clinical logic (thresholds, classifications, treatment selection).

The system exposes two interfaces sharing the same medical safety boundary (`imci_protocol.py`):

| Interface | Entry Point | Orchestration | Use Case |
|-----------|-------------|---------------|----------|
| **Gradio form UI** | `malaika/app.py` | `IMCIEngine` state machine | Step-by-step form, desktop demo |
| **Voice-first UI** | `malaika/voice_app.py` | `ChatEngine` with skills | Conversational voice, mobile-first |

The voice interface uses an **agentic skills-based architecture**: Gemma 4 reasons about which of 12 clinical skills to invoke (vision analysis, finding extraction, classification) while a deterministic protocol guard enforces IMCI step ordering. The ChatEngine emits structured events that the browser renders as skill execution cards, classification cards, and an IMCI progress bar.

### Design Philosophy
- **Two models, one runtime**: Gemma 4 for reasoning + Whisper-small for audio transcription, both via Transformers
- **Protocol-driven**: IMCI state machine is the backbone, Gemma 4 is the perception layer
- **Skills as tools**: 12 clinical skills provide typed contracts for the agentic reasoning loop
- **Modular and pluggable**: Each assessment module is independent; disable any without breaking the flow
- **Offline-complete**: Zero network calls. Every dependency is local.

---

## 2. Deployment Topology

```
┌─────────────────────────────────────────────────────────────┐
│                    DEMO MACHINE (Primary)                     │
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │  Gradio UI   │───▶│  IMCI Engine  │───▶│  Gemma 4 E4B  │  │
│  │  (app.py)    │◀───│  (state machine)│◀───│  (Transformers)│  │
│  └──────────────┘    └──────────────┘    └───────────────┘  │
│         │                    │                    │           │
│         │                    ▼                    │           │
│         │            ┌──────────────┐             │           │
│         └───────────▶│  Piper TTS   │◀────────────┘           │
│                      │  (offline)   │                         │
│                      └──────────────┘                         │
│                                                               │
│  Model: google/gemma-4-E4B-it (4-bit quantized)              │
│  VRAM: ~5-6 GB | Runtime: Transformers + BitsAndBytes         │
│  Audio: Whisper-small (244 MB) for transcription → Gemma 4    │
│  URL: Gradio share=True (public, no login)                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    ANDROID PHONE (Video Proof)                │
│                                                               │
│  ┌──────────────────────────────────────────────────┐        │
│  │  AI Edge Gallery + LiteRT-LM                      │        │
│  │  Gemma 4 E2B (base, not fine-tuned)               │        │
│  │  2.58 GB disk | 50+ tok/s | Vision + Audio        │        │
│  └──────────────────────────────────────────────────┘        │
│                                                               │
│  Purpose: 3-min video footage proving on-device capability    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    TRAINING MACHINE (GPU)                     │
│                                                               │
│  RTX 3060 (12GB) or equivalent                                │
│  Unsloth QLoRA fine-tuning of Gemma 4 E4B                    │
│  Output: LoRA adapter weights -> adapters/ directory          │
│                                                               │
│  NOT used for inference or demo.                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    COLAB NOTEBOOK (Voice Agent Demo)           │
│                                                               │
│  notebooks/10_voice_agent_colab.ipynb                         │
│  Runs voice_app.py on free Colab GPU with ngrok tunnel.       │
│  Uses ChatEngine + VoiceSessionHandler for live demo.         │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Component Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Gradio UI (app.py)                           │
│  Tabs: Assessment | History | Settings                               │
│  Inputs: Camera, Microphone, Text, Video                             │
│  Outputs: Classification cards, treatment text, TTS audio            │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    IMCI Engine (imci_engine.py)                       │
│                                                                       │
│  State Machine: DANGER -> BREATHING -> DIARRHEA -> FEVER ->          │
│                 NUTRITION -> [HEART] -> CLASSIFY -> TREAT             │
│                                                                       │
│  Each state:                                                          │
│    1. Requests specific input (image/audio/video/voice)               │
│    2. Input passes through Guards pipeline (validate -> filter)       │
│    3. Calls perception module (vision.py / audio.py)                  │
│    4. Output passes through output_validator (schema + confidence)    │
│    5. Applies WHO threshold logic (imci_protocol.py)                  │
│    6. Observability tracer records full step trace                    │
│    7. Records finding, transitions to next state                      │
└───────┬──────────┬────────────┬──────────────┬──────────────────────┘
        │          │            │              │
        ▼          ▼            ▼              ▼
┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────────────────┐
│ vision.py   │ │ audio.py    │ │ guards/     │ │ observability/       │
│             │ │             │ │             │ │                      │
│ analyze_    │ │ classify_   │ │ input_guard │ │ tracer.py            │
│  image()   │ │  breath()  │ │ content_    │ │ cost_tracker.py      │
│ analyze_    │ │ understand_ │ │  filter    │ │ feedback.py          │
│  video()   │ │  speech()  │ │ output_     │ │                      │
│ count_      │ │ analyze_    │ │  validator │ │ Every step produces  │
│  breathing()│ │  heart()   │ │             │ │ a trace entry        │
│             │ │             │ │ Every call  │ │                      │
│ ALL call    │ │ Audio→       │ │ passes all 3│ │                      │
│ Gemma 4     │ │ Whisper→     │ │ guards      │ │                      │
│             │ │ text→Gemma 4 │ │             │ │                      │
└──────┬─────┘ └──────┬─────┘ └─────────────┘ └──────────────────────┘
       │              │
       ▼              ▼
┌─────────────────────────────────────────────────────────────────────┐
│              prompts/ (PromptRegistry)                                │
│  Versioned PromptTemplate objects. NEVER hardcode prompt strings.    │
│  Each prompt: name, version, system_prompt, template, output_schema  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   MalaikaInference (inference.py)                     │
│                                                                       │
│  Single Gemma 4 E4B instance loaded once at startup.                 │
│  Self-correcting: retry with correction prompt on parse failure.     │
│  Response cache: hash-based, per-session, invalidates on reload.     │
│                                                                       │
│  Runtime: Transformers + BitsAndBytes (4-bit quantization)           │
│  VRAM: ~5-6 GB | Modalities: text, image, video                     │
│  Audio: Whisper-small (244 MB) transcribes → text → Gemma 4 reasons │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   Piper TTS (tts.py)                                  │
│                                                                       │
│  Converts Gemma 4 text output to spoken audio.                       │
│  Offline, lightweight, multiple language voices.                      │
│  NOT AI — just a speech synthesizer.                                 │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                   imci_protocol.py                                    │
│                                                                       │
│  WHO thresholds, classification logic, treatment templates.          │
│  Pure deterministic code. NO AI calls. NO imports from inference.    │
│  This is the MEDICAL SAFETY BOUNDARY.                                │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.1 Agentic Voice Architecture (voice_app.py)

The voice-first interface replaces the Gradio form with a conversational agent backed by 12 clinical skills.

```
┌─────────────────────────────────────────────────────────────────────┐
│              Voice UI (static/index.html)                             │
│  WebSocket connection for voice + structured events                   │
│  IMCI progress bar | Skill execution cards | Classification cards    │
│  Camera capture → base64 images | Mic → PCM16 audio chunks          │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ WebSocket
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│              voice_app.py (FastAPI)                                    │
│  REST: /api/chat, /api/voice, /api/image, /api/status                │
│  WS:  /ws/voice → VoiceSessionHandler                                │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│              VoiceSessionHandler (voice_session.py)                    │
│                                                                       │
│  Browser mic → PCM → Whisper-small (local STT) → transcript          │
│  ChatEngine response → sentence-level TTS → Piper (local TTS)        │
│  Filler audio during Gemma 4 thinking time                            │
│  State machine: idle → listening → thinking → speaking                │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│              ChatEngine (chat_engine.py) — Agentic Core               │
│                                                                       │
│  Maintains: BeliefState (confirmed / uncertain / pending findings)    │
│  Enforces: IMCI step ordering (greeting → danger_signs → ... →       │
│            classification → complete)                                 │
│  Selects:  Skills via Gemma 4 reasoning (tool-use pattern)           │
│  Emits structured events:                                             │
│    skill_invoked, skill_result, finding, step_change,                │
│    classification, image_request, danger_alert, assessment_complete   │
│                                                                       │
│  Each process() call returns {"text": str, "events": list[dict]}     │
└───────┬──────────┬────────────────────────────────────────────────┘
        │          │
        ▼          ▼
┌────────────┐ ┌─────────────────────────────────────────────────────┐
│ skills.py   │ │ imci_protocol.py (shared with IMCIEngine path)       │
│             │ │                                                       │
│ SkillRegistry│ │ classify_danger_signs(), classify_breathing(), ...   │
│ 12 skills:  │ │ Same deterministic WHO logic used by both interfaces │
│  assess_    │ │ This is the MEDICAL SAFETY BOUNDARY.                 │
│   alertness │ └─────────────────────────────────────────────────────┘
│  assess_    │
│   skin_color│
│  parse_     │
│   caregiver │
│  detect_    │
│   chest_    │
│   indrawing │
│  count_     │
│   breathing │
│  classify_  │
│   breath_   │
│   sounds    │
│  assess_    │
│   dehydration│
│  assess_    │
│   wasting   │
│  detect_    │
│   edema     │
│  classify_  │
│   imci_step │
│  generate_  │
│   treatment │
│  speak_to_  │
│   caregiver │
└─────────────┘
```

---

## 4. Module Boundaries and Contracts

### 4.1 inference.py — MalaikaInference

**Responsibility**: Load Gemma 4 once. Expose typed methods for each modality. Nothing else.

```
Input:  (modality_data, prompt) -> str
Output: Raw text response from Gemma 4
```

- MUST NOT parse, interpret, or apply logic to model output
- MUST NOT hold state between calls
- MUST handle GPU memory management (model loading, cleanup)
- MUST expose device/memory info for health checks

### 4.2 imci_engine.py — IMCIEngine

**Responsibility**: Orchestrate the assessment flow as a state machine.

```
Input:  User inputs (images, audio, text) at each step
Output: AssessmentResult (classifications, treatments, severity)
```

- MUST follow WHO IMCI protocol order exactly
- MUST be resumable (can pause/resume at any state)
- MUST record all findings with timestamps
- MUST NOT call Gemma 4 directly — only through vision.py / audio.py
- State transitions are deterministic — no LLM deciding the next state

### 4.3 imci_protocol.py — WHO Protocol Constants

**Responsibility**: Encode WHO IMCI thresholds and classification logic as pure functions.

```
Input:  Structured clinical findings (breathing_rate, has_indrawing, etc.)
Output: Classification (severity enum + treatment list)
```

- MUST be 100% deterministic — same input always gives same output
- MUST NOT import inference.py or call any AI
- MUST cite WHO source for every threshold
- This module IS the medical safety boundary

### 4.4 vision.py / audio.py — Perception Modules

**Responsibility**: Bridge between IMCI engine and Gemma 4 inference.

```
Input:  Raw media (image path, audio path, video path) + clinical question
Output: Structured perception result (dataclass, not raw string)
```

- MUST parse Gemma 4 output into typed dataclasses
- MUST handle parsing failures gracefully (return uncertain/unknown, never crash)
- MUST validate inputs (file exists, correct format, reasonable size)

### 4.5 app.py — Gradio UI

**Responsibility**: User interface. Capture inputs, display outputs. No logic.

```
Input:  User interactions (camera, mic, buttons)
Output: Visual assessment display, TTS audio
```

- MUST NOT contain clinical logic
- MUST NOT call inference directly — only through IMCI engine
- MUST be mobile-responsive
- MUST work without JavaScript (progressive enhancement only)

### 4.6 skills.py — SkillRegistry and BeliefState

**Responsibility**: Declare clinical skills as typed tools and track assessment knowledge.

```
SkillRegistry:  Registers 12 Skill objects with typed contracts.
                Provides lookup by name and by IMCI step.
                Generates tool descriptions for Gemma 4 system prompt.

BeliefState:    Tracks confirmed findings, uncertain findings, pending questions.
                Updated after each skill execution and caregiver response.
                Only escalates severity (green → yellow → red), never de-escalates.

SkillResult:    Typed output of skill execution (findings dict, confidence, followup).
```

- MUST NOT contain inference logic or model calls
- MUST NOT import inference.py, vision.py, or audio.py
- Skills define WHAT can be done; ChatEngine decides WHEN

### 4.7 chat_engine.py — ChatEngine (Agentic Core)

**Responsibility**: Orchestrate conversational IMCI assessment via agentic skill invocation.

```
Input:  User message (text + optional image) + current BeliefState
Output: {"text": str, "events": list[dict]}
```

- MUST enforce IMCI step ordering via deterministic guard (not LLM)
- MUST use imci_protocol.py for all classifications (never LLM output)
- MUST emit structured events for UI rendering (skill_invoked, classification, etc.)
- MUST ask one question at a time (personality constraint)
- Gemma 4 selects which skills to invoke (agentic reasoning)
- BeliefState tracks what is known vs. uncertain vs. pending

### 4.8 voice_session.py — VoiceSessionHandler

**Responsibility**: Real-time voice pipeline over a single WebSocket connection.

```
Input:  PCM16 audio chunks (browser mic) + JSON control messages
Output: TTS audio chunks (base64) + structured events (JSON)
```

- Manages STT via Whisper-small running locally (degrades to typed text input if unavailable)
- Sends ChatEngine responses as sentence-level Piper TTS chunks (fully offline)
- Plays filler audio during Gemma 4 thinking time to prevent dead air
- State machine: idle -> listening -> thinking -> speaking
- Single WebSocket per session (no separate audio/control channels)

### 4.9 voice_app.py — FastAPI Voice Server

**Responsibility**: HTTP/WebSocket server for the voice-first interface.

```
REST endpoints:
  POST /api/chat      — text message → ChatEngine → response + events
  POST /api/voice     — audio file → Whisper STT → ChatEngine → response
  POST /api/image     — image upload → stored for next ChatEngine call
  GET  /api/status    — current IMCI step, model status, session info

WebSocket:
  /ws/voice           — full-duplex voice pipeline via VoiceSessionHandler
```

- MUST NOT contain clinical logic (delegates to ChatEngine + imci_protocol)
- Serves static/index.html for the voice UI
- Creates one ChatEngine per session

### 4.10 config.py — Configuration

**Responsibility**: Single source for all configurable values.

- Feature flags (heart rate, TTS, video breathing, multilingual)
- Model paths and quantization settings
- Audio/video recording parameters
- UI configuration

### 4.11 guards/ — Three-Layer Security Pipeline

**Responsibility**: Validate, filter, and verify at every perception boundary.

```
Input:  Raw user input (file path, text) -> Validated input
Output: Model output (raw string) -> Validated structured result
```

**input_guard.py**:
- Validates file format by magic bytes (not extension)
- Enforces size limits (20MB image, 50MB audio, 200MB video)
- Rejects path traversal, symlinks, non-regular files
- Returns typed `ValidatedInput` or raises `InputValidationError`

**content_filter.py**:
- Strips null bytes, control characters from text input
- Truncates excessively long text inputs
- Wraps user content in injection-safe prompt boundaries
- Scrubs PII markers before they reach model context

**output_validator.py**:
- Validates model JSON output against prompt's `output_schema`
- Checks physiological plausibility (e.g., breathing rate 5-120, not 999)
- Enforces confidence thresholds — below threshold -> `Uncertain`
- Returns typed dataclass or triggers self-correction retry

### 4.12 observability/ — Assessment Tracing

**Responsibility**: Record what happened at every step for debugging, evaluation, and writeup evidence.

```
Input:  Step events (start, model call, parse result, classification)
Output: AssessmentTrace (list of StepTrace records)
```

**tracer.py**:
- Creates `StepTrace` per IMCI step: input hash, prompt version, raw output (truncated), parsed result, confidence, timestamp
- Produces `AssessmentTrace` for the full session — serializable to JSON
- Used for debugging, golden dataset evaluation, and writeup evidence

**cost_tracker.py**:
- Records per-call: token count (input + output), inference latency, VRAM snapshot
- Aggregates per-assessment: total tokens, total time, avg latency per step
- Feeds into performance budget validation (see Section 9)

**feedback.py**:
- Links corrections ("this was actually normal breathing") to specific trace entries
- Exports correction pairs for prompt improvement and fine-tuning data

### 4.13 Self-Correction Pattern (inference.py)

When model output cannot be parsed by `output_validator`, the system retries with a correction prompt:

```
Attempt 1: Standard prompt -> model output -> parse attempt -> FAIL
Attempt 2: Correction prompt ("Your response could not be parsed.
            Please respond ONLY with valid JSON: {schema}") -> parse -> SUCCESS/FAIL
Attempt 3: (max) Simplified prompt (fewer fields) -> parse -> SUCCESS/FAIL
Final:     Return Uncertain(raw_output=..., retries_exhausted=True)
```

- Max 2 retries (3 total attempts)
- Each retry is traced in observability
- Self-correction never changes the clinical question — only the output format instruction
- Never silently succeeds with wrong data — Uncertain is always safe

### 4.14 Response Cache (inference.py)

Hash-based cache for identical inference calls within a session.

```
cache_key = hash(prompt_version + prompt_template + media_hash + temperature)
```

- Same image analyzed twice with same prompt -> serve cached response
- Invalidated on: model reload, prompt version change, session reset
- NOT persisted across sessions (privacy: no stored media references)
- Disabled for treatment generation (may need fresh language/context)

---

## 5. Data Flow — Complete Assessment (Updated with Guards + Observability)

```
1. Caregiver opens Gradio UI on phone/browser
                    │
2. IMCI Engine starts at DANGER_SIGNS state
                    │
3. Engine requests: "Record child's appearance" (camera)
                    │
4. User captures image
                    │
5. input_guard.validate(image) -> ValidatedInput (or reject)
                    │
6. content_filter.wrap(prompt) -> injection-safe prompt
                    │
7. vision.analyze_image(image, prompt) via PromptRegistry
                    │
8. inference.generate(messages) -> raw text (check cache first)
                    │
9. output_validator.validate(raw_text, schema) -> parsed or retry
                    │
10. (If parse fails) -> self-correction retry (max 2) or Uncertain
                    │
11. vision returns: AlertnessResult(alert=False, lethargic=True, confidence=0.85)
                    │
12. tracer.record_step(input_hash, prompt_version, raw_output, parsed, confidence, latency)
                    │
13. cost_tracker.record(tokens_in, tokens_out, latency_ms)
                    │
14. Engine records finding, checks: any danger sign? -> YES
                    │
15. imci_protocol.classify_danger(findings) -> Classification.URGENT_REFERRAL
                    │
16. Engine continues to BREATHING state (assessment continues even with danger signs)
                    │
    ... (repeat steps 3-15 for each IMCI state) ...
                    │
17. Engine reaches CLASSIFY state
                    │
18. imci_protocol.aggregate_classifications(all_findings) ->
        FinalAssessment(
            classifications=[Classification.SEVERE_PNEUMONIA, Classification.URGENT_REFERRAL],
            severity=Severity.RED,
            treatments=[Treatment(...), Treatment(...)],
            referral_urgency=ReferralUrgency.IMMEDIATE
        )
                    │
13. inference.reason(treatment_prompt) -> treatment instructions in local language
                    │
14. tts.speak(treatment_text) -> audio file
                    │
15. Gradio displays: RED classification card + treatment steps + plays audio
```

### 5.1 Data Flow — Voice Pipeline (voice_app.py)

```
1. Caregiver opens voice UI on phone browser (static/index.html)
                    │
2. WebSocket connection established to /ws/voice
                    │
3. Caregiver speaks into microphone
                    │
4. Browser captures PCM16 audio (16kHz, mono) → WebSocket binary frames
                    │
5. VoiceSessionHandler receives audio
                    │
6. Audio forwarded to Whisper-small (local STT) → transcript
   (If STT unavailable: caregiver types text via REST /api/chat instead)
                    │
7. transcript → ChatEngine.process(text, image=None)
                    │
8. ChatEngine:
   a. Builds system prompt with available skills for current IMCI step
   b. Gemma 4 reasons about caregiver input, selects skills to invoke
   c. Skills execute (vision analysis, finding extraction, classification)
   d. imci_protocol.py applies WHO thresholds (deterministic)
   e. Returns {"text": response, "events": [structured events]}
                    │
9. Events forwarded to browser via WebSocket JSON messages:
   - {"type": "skill_invoked", "skill": "assess_alertness", ...}
   - {"type": "skill_result", "findings": {...}, "confidence": 0.85}
   - {"type": "finding", "key": "lethargic", "value": true}
   - {"type": "classification", "severity": "red", ...}
   - {"type": "step_change", "step": "breathing"}
   - {"type": "image_request", "prompt": "Can you show me..."}
   - {"type": "danger_alert", "message": "..."}
   - {"type": "assessment_complete", "summary": {...}}
                    │
10. Response text split at sentence boundaries for streaming TTS
                    │
11. Each sentence → Piper TTS (local) → base64 audio chunk
    (Filler audio played during Gemma 4 thinking time)
                    │
12. Browser queues audio chunks, plays sequentially
                    │
13. UI updates: IMCI progress bar, skill cards, classification cards
```

---

## 6. State Machine — IMCI Protocol

```
                    ┌──────────────┐
                    │    START     │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ DANGER_SIGNS │ vision (alertness, convulsions)
                    │              │ audio (ability to drink/breastfeed)
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  BREATHING   │ video (breathing rate)
                    │              │ vision (chest indrawing)
                    │              │ audio (wheeze, stridor, grunting)
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  DIARRHEA    │ audio/text (duration, blood in stool)
                    │              │ vision (skin pinch, sunken eyes)
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │    FEVER     │ audio/text (duration, location)
                    │              │ reasoning (malaria risk, measles)
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  NUTRITION   │ vision (visible wasting, edema)
                    │              │ text (MUAC measurement)
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐  (if enabled)
                    │  HEART_MEMS  │ audio (heart sounds from chest mic)
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │   CLASSIFY   │ imci_protocol.py (pure logic)
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │    TREAT     │ Gemma 4 generates instructions
                    │              │ Piper TTS speaks them
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │   COMPLETE   │
                    └──────────────┘
```

Each state is an enum. Transitions are explicit. No implicit state changes.

---

## 7. Dependency Graph

### Runtime Dependencies (must be offline-capable)

```
transformers          # Gemma 4 model loading and inference
torch                 # PyTorch backend
bitsandbytes          # 4-bit quantization
accelerate            # Device mapping
gradio                # Web UI (form-based interface)
fastapi               # Voice-first HTTP/WebSocket server
uvicorn               # ASGI server for FastAPI
websockets            # WebSocket client for STT/TTS services
piper-tts             # Offline text-to-speech
opencv-python-headless # Video frame extraction (if needed)
structlog             # Structured logging
pydantic              # Request/response validation (FastAPI models)
```

### Development Dependencies

```
pytest                # Testing
pytest-cov            # Coverage
mypy                  # Type checking
ruff                  # Linting + formatting
```

### Training Dependencies (separate environment)

```
unsloth               # QLoRA fine-tuning
trl                   # SFTTrainer
datasets              # HuggingFace datasets
```

### NOT Dependencies (explicitly excluded)

- No Ollama (unified Transformers runtime)
- No database (local file storage only)
- No Docker (direct Python execution for hackathon)
- No third-party speech APIs — STT is local Whisper-small, TTS is local Piper, both run in-process.

### Voice runtime (fully local)

```
Whisper-small (244 MB)   # local STT, runs in-process
Piper TTS                # local TTS, runs in-process
```

All clinical intelligence (Gemma 4 inference, IMCI classification) is fully offline.
The Gradio form interface (`app.py`) has zero external API dependencies. The web
clinical portal (`web/`) is the current connected-mode surface and uses the
browser's native MediaRecorder API for audio capture — no third-party voice SDK.

### Audio Pipeline Note

Gemma 4 E4B does **not** support native audio input (the processor ignores
the ``audios`` keyword argument). Audio is handled via a two-step pipeline:

1. **Whisper-small** (``openai/whisper-small``, 244 MB) transcribes audio to text
2. **Gemma 4** reasons on the transcription text

Both models use the Transformers library. Whisper is loaded lazily on first
audio call and can be unloaded independently of Gemma 4.

---

## 8. Error Boundaries

### Gradio Path (app.py -> IMCIEngine)

```
┌─────────────────────────────────────────────────────┐
│ UI Layer (app.py)                                    │
│  Catches: All exceptions from engine                 │
│  Shows: User-friendly error + "try again" option     │
│  Never: Crashes, shows tracebacks, hangs             │
├─────────────────────────────────────────────────────┤
│ Engine Layer (imci_engine.py)                         │
│  Catches: Perception failures, timeout               │
│  Does: Records "uncertain" finding, continues flow   │
│  Never: Skips a state, changes protocol order        │
├─────────────────────────────────────────────────────┤
│ Perception Layer (vision.py, audio.py)               │
│  Catches: Parsing failures, invalid model output     │
│  Does: Returns typed result with confidence=0.0      │
│  Never: Returns raw strings, crashes on bad input    │
├─────────────────────────────────────────────────────┤
│ Inference Layer (inference.py)                        │
│  Catches: CUDA OOM, model loading failures           │
│  Does: Raises typed exceptions (ModelError, etc.)    │
│  Never: Silently fails, returns None                 │
└─────────────────────────────────────────────────────┘
```

### Voice Path (voice_app.py -> ChatEngine)

```
┌─────────────────────────────────────────────────────┐
│ WebSocket Layer (voice_session.py)                   │
│  Catches: STT/TTS connection failures, disconnects  │
│  Does: Degrades to text-only mode, sends error msg  │
│  Never: Drops the WebSocket, loses session state    │
├─────────────────────────────────────────────────────┤
│ API Layer (voice_app.py)                             │
│  Catches: All exceptions from ChatEngine             │
│  Does: Returns error JSON, keeps session alive       │
│  Never: Crashes, exposes tracebacks to browser       │
├─────────────────────────────────────────────────────┤
│ Agent Layer (chat_engine.py)                         │
│  Catches: Skill execution failures, parse errors     │
│  Does: Records uncertain finding, asks followup      │
│  Never: Skips IMCI step, classifies without evidence │
├─────────────────────────────────────────────────────┤
│ Skill Layer (skills.py + inference.py)               │
│  Catches: Vision/audio failures, model timeouts      │
│  Does: Returns SkillResult(success=False)            │
│  Never: Returns untyped data, crashes on bad input   │
└─────────────────────────────────────────────────────┘
```

---

## 9. File Size and Performance Budgets

| Metric | Budget | Rationale |
|--------|--------|-----------|
| Model VRAM (E4B 4-bit) | < 8 GB | Must run on consumer GPU |
| Image analysis latency | < 10s | Acceptable for clinical workflow |
| Audio analysis latency | < 15s | Longer clips take more time |
| Video analysis latency | < 30s | 15s video is substantial input |
| Full IMCI assessment | < 5 min | Realistic clinical encounter time |
| Gradio cold start | < 60s | Model loading dominates |
| TTS generation | < 3s | Near-real-time spoken feedback |
| Total disk (model + app) | < 10 GB | Reasonable download |
