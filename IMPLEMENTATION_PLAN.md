# Malaika — Step-by-Step Implementation Plan

> **For Claude**: Follow this plan sequentially. Each step has exact files to create, code to write, and tests to run. Do not skip ahead. Mark completed steps with [x].
>
> **Key decisions baked in**:
> - Gemma 4 ONLY. No model switching. Ever.
> - TTS = Meta MMS-TTS (not Piper) — covers Swahili, Hausa, Yoruba
> - 5 languages: English, Swahili, Hindi, French, Hausa
> - Inference via HuggingFace Transformers (not Ollama)
> - UI via Gradio
> - Fine-tuning via Unsloth QLoRA on Mark's RTX 3060

---

## STEP 0: Project Setup

### 0.1 — Create the project structure

```
malaika/
├── CLAUDE.md                  # Dev guide for Claude sessions
├── README.md                  # Public-facing (for GitHub submission)
├── requirements.txt           # Python dependencies
├── config.py                  # All configurable settings in ONE place
├── app.py                     # Gradio app entry point
├── inference.py               # Gemma 4 model loading + all modality methods
├── tts.py                     # MMS-TTS text-to-speech engine
├── imci/
│   ├── __init__.py
│   ├── engine.py              # IMCI state machine orchestrator
│   ├── danger_signs.py        # Step 1: Danger sign assessment
│   ├── breathing.py           # Step 2: Cough/breathing assessment
│   ├── diarrhea.py            # Step 3: Diarrhea/dehydration assessment
│   ├── fever.py               # Step 4: Fever/malaria assessment
│   ├── nutrition.py           # Step 5: Nutrition/wasting assessment
│   ├── heart.py               # Step 6: Heart rate MEMS (pluggable)
│   ├── classifier.py          # Step 7: Aggregate + classify severity
│   └── treatment.py           # Step 8: Generate treatment plan
├── prompts/
│   ├── vision.py              # All vision prompts (chest indrawing, skin, wasting)
│   ├── audio.py               # All audio prompts (breath sounds, speech)
│   ├── reasoning.py           # All reasoning prompts (IMCI interpretation)
│   └── conversation.py        # All conversation prompts (caregiver Q&A)
├── data/
│   ├── imci_thresholds.json   # WHO thresholds (breathing rates, MUAC, etc.)
│   └── treatment_templates/   # Treatment instructions per classification per language
│       ├── en.json
│       ├── sw.json            # Swahili
│       ├── hi.json            # Hindi
│       ├── fr.json            # French
│       └── ha.json            # Hausa
├── training/                  # Mark's fine-tuning scripts (separate track)
│   ├── breath_sounds/
│   ├── jaundice/
│   ├── languages/
│   └── heart_sounds/
├── tests/
│   ├── test_inference.py      # Modality tests (Day 2 critical tests)
│   ├── test_imci.py           # Protocol logic tests
│   ├── test_tts.py            # TTS output tests
│   └── test_scenarios.py      # 20+ end-to-end clinical scenarios
└── assets/
    ├── demo_images/           # Test images for vision
    ├── demo_audio/            # Test audio clips
    └── demo_videos/           # Test video clips
```

### 0.2 — Create `requirements.txt`

```
# Core inference
torch>=2.1.0
transformers>=4.45.0
accelerate>=0.30.0
bitsandbytes>=0.43.0

# UI
gradio>=4.40.0

# TTS
transformers  # MMS-TTS uses transformers pipeline

# Audio processing
soundfile>=0.12.0
librosa>=0.10.0
scipy>=1.11.0

# Video processing
opencv-python>=4.9.0

# Utilities
numpy>=1.24.0
Pillow>=10.0.0
```

### 0.3 — Create `config.py`

```python
"""Single source of truth for all Malaika configuration."""

# ── Model ──────────────────────────────────────────────
MODEL_NAME = "google/gemma-4-E4B-it"
QUANTIZE_4BIT = True
MAX_NEW_TOKENS = 512

# ── Languages ──────────────────────────────────────────
SUPPORTED_LANGUAGES = {
    "en": "English",
    "sw": "Swahili",
    "hi": "Hindi",
    "fr": "French",
    "ha": "Hausa",
}
DEFAULT_LANGUAGE = "en"

# ── TTS ────────────────────────────────────────────────
# Meta MMS-TTS model IDs per language
TTS_MODELS = {
    "en": "facebook/mms-tts-eng",
    "sw": "facebook/mms-tts-swh",
    "hi": "facebook/mms-tts-hin",
    "fr": "facebook/mms-tts-fra",
    "ha": "facebook/mms-tts-hau",
}

# ── IMCI Thresholds (WHO standard) ────────────────────
# Breathing rate thresholds (breaths per minute)
FAST_BREATHING = {
    "0-2mo": 60,    # >= 60 is fast for 0-2 months
    "2-11mo": 50,   # >= 50 is fast for 2-11 months
    "12-59mo": 40,  # >= 40 is fast for 12-59 months
}

# MUAC thresholds (mm)
MUAC_SEVERE = 115      # < 115mm = severe acute malnutrition
MUAC_MODERATE = 125    # 115-125mm = moderate acute malnutrition

# ── Features (toggle on/off) ──────────────────────────
ENABLE_HEART_RATE = True    # Set False to disable MEMS module
ENABLE_VIDEO_BREATHING = True  # Set False to use image-based fallback

# ── Gradio ─────────────────────────────────────────────
GRADIO_SHARE = True     # Public URL for judges
GRADIO_SERVER_PORT = 7860

# ── Paths ──────────────────────────────────────────────
TREATMENT_TEMPLATES_DIR = "data/treatment_templates"
IMCI_THRESHOLDS_PATH = "data/imci_thresholds.json"
```

### 0.4 — Create `CLAUDE.md` (dev guide for future sessions)

This file tells Claude how to work on the project in any future session. Include:
- Project overview (one paragraph)
- Tech stack (Gemma 4 E4B, Transformers, Gradio, MMS-TTS, Unsloth)
- Key rules: everything offline, everything Gemma 4, no model switching
- How to run: `python app.py`
- How to test: `python -m pytest tests/`
- File map (which file does what)
- The 5 supported languages and their codes

### 0.5 — Initialize git repo

```bash
cd malaika/
git init
# Create .gitignore: __pycache__, *.pyc, .env, models/, *.wav, *.mp4 (large files)
git add -A
git commit -m "Initial project structure"
```

---

## STEP 1: Inference Engine (`inference.py`)

This is the brain. One class. One model load. All modalities.

### 1.1 — Write `inference.py`

```python
"""Gemma 4 E4B inference — text, image, audio, video through one model."""

from transformers import AutoProcessor, AutoModelForMultimodalLM, BitsAndBytesConfig
import torch
from config import MODEL_NAME, QUANTIZE_4BIT, MAX_NEW_TOKENS


class MalaikaInference:
    def __init__(self):
        self.processor = AutoProcessor.from_pretrained(MODEL_NAME)

        load_kwargs = {"device_map": "auto"}
        if QUANTIZE_4BIT:
            load_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
            )

        self.model = AutoModelForMultimodalLM.from_pretrained(
            MODEL_NAME, **load_kwargs
        )

    def _generate(self, messages: list, max_tokens: int = MAX_NEW_TOKENS) -> str:
        inputs = self.processor.apply_chat_template(
            messages,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
            add_generation_prompt=True,
        ).to(self.model.device)
        outputs = self.model.generate(**inputs, max_new_tokens=max_tokens)
        return self.processor.decode(outputs[0], skip_special_tokens=True)

    def analyze_image(self, image_path: str, prompt: str) -> str:
        return self._generate([{
            "role": "user",
            "content": [
                {"type": "image", "image": image_path},
                {"type": "text", "text": prompt},
            ],
        }])

    def analyze_audio(self, audio_path: str, prompt: str) -> str:
        return self._generate([{
            "role": "user",
            "content": [
                {"type": "audio", "audio": audio_path},
                {"type": "text", "text": prompt},
            ],
        }])

    def analyze_video(self, video_path: str, prompt: str) -> str:
        return self._generate([{
            "role": "user",
            "content": [
                {"type": "video", "video": video_path},
                {"type": "text", "text": prompt},
            ],
        }])

    def reason(self, prompt: str, system: str = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self._generate(messages)

    def converse(self, history: list[dict], user_input: str) -> str:
        """Multi-turn conversation. history = list of {role, content} dicts."""
        messages = history + [{"role": "user", "content": user_input}]
        return self._generate(messages)
```

### 1.2 — Day 2 critical tests (`tests/test_inference.py`)

These MUST pass before anything else proceeds. Write tests for:

1. **Model loads in <8GB VRAM** — measure `torch.cuda.memory_allocated()`
2. **Image analysis works** — send a test photo, get text back
3. **Audio speech understanding works** — send a WAV of English speech, check it transcribes/understands
4. **Audio breath sound classification** — send an ICBHI sample, ask "is this wheezing or normal?"
5. **Video breathing rate** — send a 15s chest video, ask to count rises
6. **Latency** — time each call, record results
7. **Swahili text** — ask model to respond in Swahili, check it does
8. **Swahili audio** — send Swahili speech, check comprehension

**Record ALL results in a `DAY2_RESULTS.md` file.** These results determine the approach for breathing rate and audio classification going forward.

---

## STEP 2: TTS Engine (`tts.py`)

### 2.1 — Write `tts.py` using Meta MMS-TTS

```python
"""Text-to-speech using Meta MMS-TTS. Supports 1,100+ languages offline."""

from transformers import VitsModel, AutoTokenizer
import torch
import scipy.io.wavfile
from config import TTS_MODELS, DEFAULT_LANGUAGE


class MalaikaTTS:
    def __init__(self):
        self._models = {}  # Lazy-loaded per language

    def _load_model(self, lang_code: str):
        if lang_code not in self._models:
            model_id = TTS_MODELS.get(lang_code, TTS_MODELS[DEFAULT_LANGUAGE])
            self._models[lang_code] = {
                "model": VitsModel.from_pretrained(model_id),
                "tokenizer": AutoTokenizer.from_pretrained(model_id),
            }
        return self._models[lang_code]

    def speak(self, text: str, lang_code: str = DEFAULT_LANGUAGE) -> str:
        """Convert text to speech. Returns path to WAV file."""
        m = self._load_model(lang_code)
        inputs = m["tokenizer"](text, return_tensors="pt")
        with torch.no_grad():
            output = m["model"](**inputs).waveform
        output_path = f"/tmp/malaika_tts_{lang_code}.wav"
        scipy.io.wavfile.write(
            output_path,
            rate=m["model"].config.sampling_rate,
            data=output.float().numpy().squeeze(),
        )
        return output_path
```

### 2.2 — Test TTS for all 5 languages

Write `tests/test_tts.py`:
- Generate speech in each of the 5 languages
- Verify WAV files are created and non-empty
- Manually listen to verify quality

---

## STEP 3: IMCI Protocol Engine

This is the clinical brain. It's a state machine — deterministic code that calls Gemma 4 for perception at each step.

### 3.1 — Write `data/imci_thresholds.json`

```json
{
  "breathing_rate": {
    "0-2mo": {"fast": 60, "unit": "breaths/min"},
    "2-11mo": {"fast": 50, "unit": "breaths/min"},
    "12-59mo": {"fast": 40, "unit": "breaths/min"}
  },
  "muac": {
    "severe": 115,
    "moderate": 125,
    "unit": "mm"
  },
  "danger_signs": [
    "unable_to_drink_or_breastfeed",
    "vomits_everything",
    "convulsions",
    "lethargic_or_unconscious"
  ],
  "dehydration_signs": {
    "severe": ["lethargic_or_unconscious", "sunken_eyes", "skin_pinch_very_slow"],
    "some": ["restless_irritable", "sunken_eyes", "skin_pinch_slow", "drinks_eagerly"],
    "none": ["no_signs"]
  }
}
```

### 3.2 — Write `imci/engine.py` (the orchestrator)

```python
"""IMCI Protocol Engine — orchestrates the full assessment flow."""

from enum import Enum
from dataclasses import dataclass, field

class AssessmentState(Enum):
    WELCOME = "welcome"
    CHILD_AGE = "child_age"
    DANGER_SIGNS = "danger_signs"
    BREATHING = "breathing"
    DIARRHEA = "diarrhea"
    FEVER = "fever"
    NUTRITION = "nutrition"
    HEART = "heart"
    CLASSIFICATION = "classification"
    TREATMENT = "treatment"
    COMPLETE = "complete"

@dataclass
class AssessmentData:
    """Accumulates findings across all steps."""
    age_months: int = 0
    language: str = "en"

    # Danger signs
    danger_signs: list[str] = field(default_factory=list)
    has_danger_sign: bool = False

    # Breathing
    breathing_rate: int = 0
    has_fast_breathing: bool = False
    has_chest_indrawing: bool = False
    has_stridor: bool = False
    has_wheezing: bool = False
    breath_sound_classification: str = ""

    # Diarrhea
    has_diarrhea: bool = False
    diarrhea_duration_days: int = 0
    has_blood_in_stool: bool = False
    dehydration_level: str = "none"  # none, some, severe

    # Fever
    has_fever: bool = False
    fever_duration_days: int = 0
    in_malaria_area: bool = False

    # Nutrition
    muac_mm: int = 0
    has_visible_wasting: bool = False
    has_edema: bool = False

    # Heart (optional)
    heart_rate_bpm: int = 0
    heart_abnormality: str = ""

    # Classification
    classifications: dict = field(default_factory=dict)
    overall_severity: str = ""  # green, yellow, red
    treatment_plan: str = ""


class IMCIEngine:
    """State machine that walks through the IMCI protocol step by step."""

    def __init__(self, inference, tts):
        self.inference = inference  # MalaikaInference instance
        self.tts = tts              # MalaikaTTS instance
        self.state = AssessmentState.WELCOME
        self.data = AssessmentData()

        # Import step handlers
        from imci.danger_signs import assess_danger_signs
        from imci.breathing import assess_breathing
        from imci.diarrhea import assess_diarrhea
        from imci.fever import assess_fever
        from imci.nutrition import assess_nutrition
        from imci.heart import assess_heart
        from imci.classifier import classify
        from imci.treatment import generate_treatment

        self.steps = {
            AssessmentState.DANGER_SIGNS: assess_danger_signs,
            AssessmentState.BREATHING: assess_breathing,
            AssessmentState.DIARRHEA: assess_diarrhea,
            AssessmentState.FEVER: assess_fever,
            AssessmentState.NUTRITION: assess_nutrition,
            AssessmentState.HEART: assess_heart,
            AssessmentState.CLASSIFICATION: classify,
            AssessmentState.TREATMENT: generate_treatment,
        }

    def get_next_state(self) -> AssessmentState:
        """Determines the next state in the protocol."""
        order = [
            AssessmentState.WELCOME,
            AssessmentState.CHILD_AGE,
            AssessmentState.DANGER_SIGNS,
            AssessmentState.BREATHING,
            AssessmentState.DIARRHEA,
            AssessmentState.FEVER,
            AssessmentState.NUTRITION,
            AssessmentState.HEART,
            AssessmentState.CLASSIFICATION,
            AssessmentState.TREATMENT,
            AssessmentState.COMPLETE,
        ]
        current_idx = order.index(self.state)
        if current_idx + 1 < len(order):
            return order[current_idx + 1]
        return AssessmentState.COMPLETE

    def advance(self, user_input=None, image=None, audio=None, video=None):
        """Process input for current state, return response, advance state."""
        self.state = self.get_next_state()

        if self.state in self.steps:
            response = self.steps[self.state](
                self.inference, self.data,
                user_input=user_input,
                image=image,
                audio=audio,
                video=video,
            )
            return response

        if self.state == AssessmentState.WELCOME:
            return self._welcome()
        if self.state == AssessmentState.CHILD_AGE:
            return self._ask_age()
        if self.state == AssessmentState.COMPLETE:
            return self._complete()

        return "Assessment complete."

    def _welcome(self):
        return ("I am Malaika, your child health assistant. "
                "I will guide you through a health check for your child. "
                "Let's begin.")

    def _ask_age(self):
        return "How old is your child? Please tell me in months or years."

    def _complete(self):
        return ("The assessment is complete. "
                f"Overall: {self.data.overall_severity}. "
                f"{self.data.treatment_plan}")
```

### 3.3 — Write each IMCI step module

Each step file follows the same pattern:

```python
# imci/danger_signs.py
def assess_danger_signs(inference, data, user_input=None, image=None, audio=None, video=None):
    """
    WHO IMCI Danger Signs:
    1. Unable to drink or breastfeed
    2. Vomits everything
    3. Convulsions (now or recent)
    4. Lethargic or unconscious

    Uses: voice (caregiver answers) + vision (child alertness)
    """
    findings = []

    # If we have an image, check alertness
    if image:
        alertness = inference.analyze_image(
            image,
            "Look at this child. Is the child: (a) alert and active, "
            "(b) drowsy or lethargic, or (c) unconscious? "
            "Describe what you see about the child's alertness level."
        )
        findings.append(f"Visual alertness: {alertness}")

    # If we have audio, understand what caregiver reports
    if audio:
        report = inference.analyze_audio(
            audio,
            "A caregiver is describing their child's symptoms. "
            "Extract: Can the child drink or breastfeed? "
            "Has the child vomited everything? "
            "Has the child had convulsions? "
            "Report each as yes, no, or unclear."
        )
        findings.append(f"Caregiver report: {report}")

    # Parse findings into structured data
    if findings:
        parsed = inference.reason(
            f"Based on these observations:\n"
            + "\n".join(findings) +
            "\n\nFor each WHO IMCI danger sign, classify as PRESENT or ABSENT:\n"
            "1. Unable to drink or breastfeed: \n"
            "2. Vomits everything: \n"
            "3. Convulsions: \n"
            "4. Lethargic or unconscious: \n"
            "Respond in exactly this format."
        )
        # Parse response and update data.danger_signs, data.has_danger_sign
        # ... (parsing logic)

    prompt = ("I need to check for danger signs. "
              "Can your child drink or breastfeed? "
              "Has your child vomited everything today? "
              "Has your child had convulsions?")
    return prompt
```

**Write similar files for:**

| File | What Gemma 4 does | What code does |
|------|-------------------|----------------|
| `imci/breathing.py` | Counts breathing from video, classifies breath sounds from audio, detects chest indrawing from image | Compares rate to WHO age thresholds |
| `imci/diarrhea.py` | Understands duration/blood via voice, observes skin pinch via camera | Applies WHO dehydration matrix |
| `imci/fever.py` | Conversational assessment via voice | Applies WHO fever rules |
| `imci/nutrition.py` | Visual wasting from camera, guides MUAC | Compares MUAC to thresholds |
| `imci/heart.py` | Analyzes heart sounds (if enabled) | Estimates BPM, flags abnormalities |
| `imci/classifier.py` | None — pure deterministic code | Aggregates all findings → red/yellow/green |
| `imci/treatment.py` | Generates instructions in caregiver's language | Selects template, Gemma 4 localizes |

### 3.4 — Write `imci/classifier.py` (pure logic, no AI)

```python
def classify(inference, data, **kwargs):
    """WHO IMCI classification — deterministic logic only."""
    classifications = {}

    # ── Pneumonia classification ─────────────────────
    if data.has_danger_sign and (data.has_chest_indrawing or data.has_stridor):
        classifications["pneumonia"] = "severe_pneumonia"  # RED
    elif data.has_fast_breathing or data.has_chest_indrawing:
        classifications["pneumonia"] = "pneumonia"  # YELLOW
    elif not data.has_fast_breathing:
        classifications["pneumonia"] = "no_pneumonia"  # GREEN (cough/cold)

    # ── Diarrhea classification ──────────────────────
    if data.has_diarrhea:
        if data.dehydration_level == "severe":
            classifications["diarrhea"] = "severe_dehydration"  # RED
        elif data.dehydration_level == "some":
            classifications["diarrhea"] = "some_dehydration"  # YELLOW
        else:
            classifications["diarrhea"] = "no_dehydration"  # GREEN

    # ── Fever classification ─────────────────────────
    if data.has_fever:
        if data.has_danger_sign:
            classifications["fever"] = "very_severe_febrile_disease"  # RED
        elif data.in_malaria_area:
            classifications["fever"] = "malaria"  # YELLOW
        else:
            classifications["fever"] = "fever_no_malaria"  # YELLOW

    # ── Nutrition classification ─────────────────────
    if data.has_edema or data.muac_mm < 115:
        classifications["nutrition"] = "severe_malnutrition"  # RED
    elif data.muac_mm < 125 or data.has_visible_wasting:
        classifications["nutrition"] = "moderate_malnutrition"  # YELLOW
    else:
        classifications["nutrition"] = "no_malnutrition"  # GREEN

    # ── Overall severity ─────────────────────────────
    data.classifications = classifications
    if any(v in ["severe_pneumonia", "severe_dehydration",
                  "very_severe_febrile_disease", "severe_malnutrition"]
           for v in classifications.values()) or data.has_danger_sign:
        data.overall_severity = "red"
    elif any(v in ["pneumonia", "some_dehydration", "malaria",
                    "fever_no_malaria", "moderate_malnutrition"]
             for v in classifications.values()):
        data.overall_severity = "yellow"
    else:
        data.overall_severity = "green"

    return f"Classification complete: {data.overall_severity.upper()}"
```

### 3.5 — Write `imci/treatment.py`

```python
def generate_treatment(inference, data, **kwargs):
    """Generate treatment instructions in caregiver's language."""
    lang = data.language

    # Build context from classifications
    findings_summary = "\n".join(
        f"- {k}: {v}" for k, v in data.classifications.items()
    )

    treatment = inference.reason(
        f"You are a WHO IMCI clinical decision support tool.\n"
        f"A child aged {data.age_months} months has these classifications:\n"
        f"{findings_summary}\n"
        f"Overall severity: {data.overall_severity}\n\n"
        f"Generate clear, step-by-step treatment instructions "
        f"following WHO IMCI guidelines.\n"
        f"Respond in {SUPPORTED_LANGUAGES.get(lang, 'English')}.\n"
        f"Use simple language a mother with no medical training can follow.\n"
        f"If RED: emphasize urgency and what to do during transport.\n"
        f"If YELLOW: home treatment steps + when to return.\n"
        f"If GREEN: reassurance + home care + warning signs to watch.",
        system="You are Malaika, a child health assistant following WHO IMCI protocol."
    )

    data.treatment_plan = treatment
    return treatment
```

---

## STEP 4: Prompt Library (`prompts/`)

### 4.1 — Write `prompts/vision.py`

Store all vision prompts as constants. Each prompt is carefully engineered for medical accuracy.

```python
CHEST_INDRAWING = (
    "Examine this image of a child's chest/torso area. "
    "Look for subcostal chest indrawing — the lower chest wall "
    "pulling inward when the child breathes in. "
    "This is different from normal soft tissue movement. "
    "Report: (1) Is chest indrawing present? (yes/no) "
    "(2) Confidence level (high/medium/low) "
    "(3) What you observed."
)

SKIN_COLOR = (
    "Examine this image of a child's skin. Assess for: "
    "(1) Jaundice — yellow coloring of skin/eyes (check sclera if visible) "
    "(2) Cyanosis — blue/grey coloring of lips, fingertips, or skin "
    "(3) Pallor — unusual paleness of palms, conjunctiva, or nail beds "
    "Report each as: present / absent / cannot determine. "
    "Include confidence level."
)

WASTING = (
    "Examine this image of a child. Assess for visible severe wasting: "
    "(1) Are the ribs clearly visible? "
    "(2) Is there loss of fat on buttocks? "
    "(3) Does the child appear severely thin? "
    "Report: visible wasting (yes/no), confidence (high/medium/low)."
)

BREATHING_RATE_VIDEO = (
    "Watch this video of a child's chest. "
    "Count the number of times the chest rises (one rise = one breath). "
    "The video is {duration} seconds long. "
    "Report: (1) Number of chest rises counted "
    "(2) Calculated breaths per minute "
    "(3) Confidence in your count (high/medium/low)."
)

SKIN_PINCH = (
    "Watch the skin pinch test being performed on this child's abdomen. "
    "After the skin is pinched and released, observe how quickly it returns: "
    "(1) Immediately (normal) "
    "(2) Slowly — takes 1-2 seconds (some dehydration) "
    "(3) Very slowly — more than 2 seconds (severe dehydration) "
    "Report which category and your confidence."
)

CHILD_ALERTNESS = (
    "Look at this child. Assess their level of consciousness: "
    "(1) Alert — eyes open, responsive, active "
    "(2) Drowsy/lethargic — difficult to wake, not alert "
    "(3) Unconscious — does not respond "
    "Report the level and what you observe."
)
```

### 4.2 — Write `prompts/audio.py`

```python
BREATH_SOUNDS = (
    "Listen to this audio recording of a child's breathing. "
    "Classify the breathing sounds as: "
    "(1) Normal — clear breathing "
    "(2) Wheeze — high-pitched whistling on exhale "
    "(3) Stridor — harsh sound on inhale (indicates airway obstruction) "
    "(4) Grunting — short sounds on each exhale (indicates respiratory distress) "
    "(5) Crackles — bubbling or rattling sounds "
    "Report: primary classification, confidence, and description."
)

SPEECH_UNDERSTANDING = (
    "A caregiver is speaking about their sick child. "
    "Listen carefully and extract: "
    "(1) What symptoms are they describing? "
    "(2) How long has the child been sick? "
    "(3) Any treatments already tried? "
    "(4) The language they are speaking in. "
    "Respond in English with structured answers."
)

COUGH_ASSESSMENT = (
    "Listen to this audio. Is the child coughing? "
    "If yes: (1) Is it a dry cough or wet/productive cough? "
    "(2) Is it severe (continuous, distressing) or mild? "
    "(3) Any whooping sound (could indicate pertussis)? "
    "Report findings."
)
```

### 4.3 — Write `prompts/conversation.py`

```python
SYSTEM_PROMPT = (
    "You are Malaika, a child health assessment assistant following "
    "the WHO IMCI protocol. You speak to caregivers in their language. "
    "Be warm, calm, and reassuring. Use simple words. "
    "Ask one question at a time. Guide them step by step."
)

def get_question(step: str, language: str) -> str:
    """Generate the right question for each IMCI step."""
    questions = {
        "age": "How old is your child? Tell me in months or years.",
        "chief_complaint": "What is wrong with your child? Tell me what you have noticed.",
        "drinking": "Can your child drink or breastfeed?",
        "vomiting": "Has your child vomited everything today?",
        "convulsions": "Has your child had fits or convulsions?",
        "diarrhea_presence": "Does your child have diarrhea — loose or watery stools?",
        "diarrhea_duration": "How many days has the diarrhea lasted?",
        "blood_in_stool": "Have you seen blood in the stool?",
        "fever_presence": "Does your child have fever or feel hot?",
        "fever_duration": "How many days has the fever lasted?",
        "cough_presence": "Does your child have a cough?",
        "cough_duration": "How many days has the cough lasted?",
    }
    return questions.get(step, "")
```

---

## STEP 5: Gradio UI (`app.py`)

### 5.1 — Build the Gradio interface

The UI has these tabs/sections:

1. **Welcome** — language selector, start button
2. **Assessment** — main screen showing:
   - Current step (e.g., "Step 2: Breathing Assessment")
   - Camera input (for vision steps)
   - Mic input (for voice/audio steps)
   - Text display of AI response
   - Audio playback of TTS response
   - Progress bar (which steps done)
3. **Results** — traffic-light classification display with treatment plan

```python
# app.py — entry point
import gradio as gr
from inference import MalaikaInference
from tts import MalaikaTTS
from imci.engine import IMCIEngine
from config import SUPPORTED_LANGUAGES, GRADIO_SHARE, GRADIO_SERVER_PORT

# Load model ONCE at startup
inference = MalaikaInference()
tts = MalaikaTTS()

def start_assessment(language):
    engine = IMCIEngine(inference, tts)
    engine.data.language = language
    response = engine.advance()
    audio = tts.speak(response, language)
    return engine, response, audio

def process_step(engine, text_input, image, audio_input):
    response = engine.advance(
        user_input=text_input,
        image=image,
        audio=audio_input,
    )
    audio_out = tts.speak(response, engine.data.language)
    severity = engine.data.overall_severity
    return engine, response, audio_out, severity

# Build Gradio interface with:
# - Language dropdown
# - Image upload / webcam
# - Audio recorder
# - Text input (fallback)
# - Response text display
# - Audio output player
# - Severity indicator (colored box)
# - Step progress display
```

### 5.2 — Key Gradio components to use

- `gr.Dropdown` — language selection
- `gr.Image(sources=["webcam", "upload"])` — camera/photo input
- `gr.Audio(sources=["microphone"])` — mic input
- `gr.Textbox` — text fallback + response display
- `gr.Audio(autoplay=True)` — TTS output
- `gr.HTML` — severity color indicator (red/yellow/green box)
- `gr.State` — holds the engine instance between interactions

### 5.3 — Mobile-responsive

Add custom CSS to make it work well on phone screens (judges may test on mobile):
- Large buttons
- Single column layout
- Big text
- Auto-play audio responses

---

## STEP 6: Treatment Templates (`data/treatment_templates/`)

### 6.1 — Create `en.json` first, then translate

```json
{
  "severe_pneumonia": {
    "severity": "red",
    "title": "URGENT: Severe Pneumonia",
    "instructions": [
      "This is an emergency. Go to the nearest health facility immediately.",
      "Keep the child warm during transport.",
      "If the child can drink, give small sips of water on the way.",
      "Do not give any medicine before seeing a health worker.",
      "Tell the health worker: the child has fast breathing and chest indrawing."
    ]
  },
  "pneumonia": {
    "severity": "yellow",
    "title": "Pneumonia — Needs Antibiotics",
    "instructions": [
      "Go to the nearest health facility within 24 hours.",
      "The health worker will give amoxicillin.",
      "Give the child plenty of fluids and continue breastfeeding.",
      "If the child gets worse before you reach the facility, go immediately."
    ]
  },
  "no_pneumonia": {
    "severity": "green",
    "title": "Cough or Cold — Treat at Home",
    "instructions": [
      "Give warm fluids to soothe the throat.",
      "Continue breastfeeding.",
      "Keep the child's nose clear.",
      "Return if: breathing becomes fast, child cannot drink, child gets sicker."
    ]
  }
}
```

Create similar entries for: `severe_dehydration`, `some_dehydration`, `no_dehydration`, `malaria`, `fever_no_malaria`, `severe_malnutrition`, `moderate_malnutrition`.

### 6.2 — Translate to other languages

Use Gemma 4 itself to translate the templates:

```python
for lang in ["sw", "hi", "fr", "ha"]:
    translated = inference.reason(
        f"Translate the following medical instructions to {language_name}. "
        f"Use simple, everyday words that a mother would understand. "
        f"Do not use medical jargon.\n\n{english_instructions}"
    )
```

Save as `sw.json`, `hi.json`, `fr.json`, `ha.json`.

---

## STEP 7: Testing (20+ scenarios)

### 7.1 — Write `tests/test_scenarios.py`

Each scenario simulates a complete assessment with predefined inputs and expected classifications:

```python
SCENARIOS = [
    {
        "name": "Fast breathing, no other signs",
        "age_months": 8,
        "breathing_rate": 55,
        "chest_indrawing": False,
        "expected_pneumonia": "pneumonia",
        "expected_severity": "yellow",
    },
    {
        "name": "Chest indrawing + stridor + danger sign",
        "age_months": 14,
        "breathing_rate": 52,
        "chest_indrawing": True,
        "stridor": True,
        "has_danger_sign": True,
        "expected_pneumonia": "severe_pneumonia",
        "expected_severity": "red",
    },
    # ... 18 more scenarios
]
```

### 7.2 — Write `tests/test_imci.py`

Unit tests for the classifier logic (no model needed — pure Python):
- Every threshold boundary (39 vs 40 breaths/min for 12-59mo)
- Every danger sign combination
- Every dehydration level
- Every severity aggregation

---

## STEP 8: Fine-Tuning (Mark's Track)

### 8.1 — `training/breath_sounds/train.py`

Unsloth QLoRA script for ICBHI dataset:
- Download ICBHI 2017 from Kaggle
- Format as instruction pairs: `{audio: "path.wav", prompt: "classify", response: "wheeze"}`
- Train with Unsloth on RTX 3060 (script from MASTERPLAN section 4)
- Export merged model or adapter weights

### 8.2 — `training/jaundice/train.py`

- Download Mendeley + NJN datasets
- Format as instruction pairs: `{image: "path.jpg", prompt: "assess skin", response: "jaundice present, moderate"}`
- Train vision LoRA

### 8.3 — `training/languages/train.py`

- Download WAXAL subset (Swahili, Hausa, Yoruba)
- Format as instruction pairs
- Train audio/language LoRA

### 8.4 — `training/heart_sounds/train.py` (if MEMS GO)

- Download CirCor from PhysioNet
- Format as instruction pairs
- Train audio LoRA

### 8.5 — Loading adapters in inference

After training, update `inference.py` to load LoRA adapters:

```python
from peft import PeftModel

# Load base model, then apply adapter
self.model = PeftModel.from_pretrained(self.model, "path/to/adapter")
```

---

## STEP 9: Deployment

### 9.1 — Local demo (Gradio share)

```bash
python app.py
# Gradio creates a public URL like https://xxxxx.gradio.live
# Share this URL with judges
```

### 9.2 — Cloud GPU fallback

If local machine can't run it, deploy to:
- **Google Colab Pro** (A100, free tier may work)
- **Hugging Face Spaces** (GPU spaces)
- **RunPod** / **Vast.ai** (cheap GPU rental)

Run `app.py` on the cloud GPU, use `share=True` for public URL.

### 9.3 — Phone demo (for video only)

- Install AI Edge Gallery on Android phone
- Download Gemma 4 E2B LiteRT model
- Record video of it running on phone
- This is BASE model (not fine-tuned) — that's fine and honest

---

## STEP 10: Video + Submission

### 10.1 — Video (3 minutes)

Follow the script from MALAIKA_PROPOSAL.md:
- [0:00-0:15] The Number (4.9 million)
- [0:15-0:30] The Gap (WHO manuals vs. villages)
- [0:30-0:45] The Contrast ("they said open source can't...")
- [0:45-1:15] The Turn (mother opens Malaika)
- [1:15-2:00] The Assessment (technical showcase, all modalities)
- [2:00-2:20] The Verdict (red/yellow/green)
- [2:20-2:40] The Scale (multiple countries/languages)
- [2:40-3:00] The Close

### 10.2 — Kaggle writeup (1,500 words max)

Structure:
1. Problem (200 words) — 4.9M stat, the gap
2. Solution (300 words) — what Malaika does, IMCI protocol
3. Technical architecture (400 words) — Gemma 4 modalities, state machine, fine-tuning
4. Results (300 words) — accuracy metrics, test scenarios
5. Impact (200 words) — scale, accessibility, why it matters
6. Demo link + repo link

### 10.3 — Submission checklist

- [ ] Kaggle writeup submitted (not draft!)
- [ ] YouTube video (3 min, public, unlisted OK)
- [ ] GitHub repo (public, documented, no secrets)
- [ ] Live demo URL (Gradio share or cloud)
- [ ] Cover image + screenshots
- [ ] Track: Health & Sciences

---

## Execution Order Summary

```
Week 1 (Apr 12-18):  Steps 0-2  → Repo + inference + TTS working
Week 2 (Apr 19-25):  Steps 3-4  → Full IMCI protocol + prompts
Week 3 (Apr 26-May 2): Step 5-6 → Gradio UI + treatment templates
Week 4 (May 3-9):    Steps 7-9  → Testing + fine-tuning + deployment
Week 5 (May 10-18):  Step 10    → Video + writeup + submit
```

Mark's fine-tuning (Step 8) runs in parallel throughout weeks 1-4.

---

*Implementation Plan v1 — April 12, 2026*
*Based on MASTERPLAN.md v3 + TTS and language decisions from team discussion*
