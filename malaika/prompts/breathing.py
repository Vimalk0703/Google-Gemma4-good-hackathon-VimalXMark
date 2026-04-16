"""Breathing assessment prompts — IMCI cough/difficulty breathing.

Covers: respiratory rate counting from video, chest indrawing detection,
and breath sound classification (wheeze, stridor, grunting, crackles).
"""

from malaika.prompts.base import PromptTemplate
from malaika.prompts import PromptRegistry
from malaika.prompts.system import SYSTEM_MEDICAL_OBSERVER


# --- Breathing Rate from Video ---
# (Exact version from docs/PROMPT_ENGINEERING.md)
COUNT_BREATHING_RATE = PromptRegistry.register(PromptTemplate(
    name="breathing.count_rate_from_video",
    version="1.0.0",
    description="Count chest rise/fall cycles in a 15-second video clip.",
    system_prompt=SYSTEM_MEDICAL_OBSERVER,
    user_template=(
        "This is a {duration_seconds}-second video of a child's chest. "
        "Count the number of complete breathing cycles (one cycle = chest rises then falls). "
        "Report ONLY a JSON object: "
        '{{"breath_count": <integer>, "confidence": <0.0-1.0>, '
        '"notes": "<any observations about breathing pattern>"}}'
    ),
    required_variables=frozenset({"duration_seconds"}),
    expected_output_format="json",
    output_schema={
        "type": "object",
        "properties": {
            "breath_count": {"type": "integer"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "notes": {"type": "string"},
        },
        "required": ["breath_count", "confidence"],
    },
    max_tokens=150,
    temperature=0.0,
))


# --- Chest Indrawing from Image ---
DETECT_CHEST_INDRAWING = PromptRegistry.register(PromptTemplate(
    name="breathing.detect_chest_indrawing",
    version="1.0.0",
    description="Detect subcostal/intercostal chest indrawing from a chest image.",
    system_prompt=SYSTEM_MEDICAL_OBSERVER,
    user_template=(
        "Examine this image of a child's chest and lower ribcage. "
        "Determine if there is subcostal chest indrawing "
        "(the lower chest wall goes IN when the child breathes IN). "
        "Report ONLY a JSON object: "
        '{{"indrawing_detected": true/false, "confidence": <0.0-1.0>, '
        '"location": "<subcostal|intercostal|both|none>", '
        '"description": "<what you observe>"}}'
    ),
    required_variables=frozenset(),
    expected_output_format="json",
    output_schema={
        "type": "object",
        "properties": {
            "indrawing_detected": {"type": "boolean"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "location": {
                "type": "string",
                "enum": ["subcostal", "intercostal", "both", "none"],
            },
            "description": {"type": "string"},
        },
        "required": ["indrawing_detected", "confidence", "location"],
    },
    max_tokens=200,
    temperature=0.0,
))


# --- Breath Sound Classification from Audio (original — kept for future native audio support) ---
CLASSIFY_BREATH_SOUNDS = PromptRegistry.register(PromptTemplate(
    name="breathing.classify_breath_sounds",
    version="1.0.0",
    description="Classify breath sounds from audio recording (wheeze, stridor, grunting, crackles, normal).",
    system_prompt=SYSTEM_MEDICAL_OBSERVER,
    user_template=(
        "This is an audio recording of a child's breathing captured by a phone microphone "
        "placed near the child's chest/mouth. "
        "Classify the breath sounds you hear. "
        "Report ONLY a JSON object: "
        '{{"wheeze": true/false, "stridor": true/false, "grunting": true/false, '
        '"crackles": true/false, "normal": true/false, '
        '"confidence": <0.0-1.0>, '
        '"description": "<what you hear>"}}'
    ),
    required_variables=frozenset(),
    expected_output_format="json",
    output_schema={
        "type": "object",
        "properties": {
            "wheeze": {"type": "boolean"},
            "stridor": {"type": "boolean"},
            "grunting": {"type": "boolean"},
            "crackles": {"type": "boolean"},
            "normal": {"type": "boolean"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "description": {"type": "string"},
        },
        "required": ["wheeze", "stridor", "grunting", "crackles", "normal", "confidence"],
    },
    max_tokens=200,
    temperature=0.0,
))


# --- Breath Sound Classification from Spectrogram Image (audio → spectrogram → Gemma 4 vision) ---
CLASSIFY_BREATH_SOUNDS_FROM_SPECTROGRAM = PromptRegistry.register(PromptTemplate(
    name="breathing.classify_breath_sounds_from_spectrogram",
    version="1.0.0",
    description=(
        "Classify breath sounds from a mel-spectrogram image of an audio recording. "
        "The spectrogram shows frequency (vertical axis, low to high) vs time (horizontal). "
        "Gemma 4 vision analyzes the visual patterns to detect abnormal breath sounds."
    ),
    system_prompt=SYSTEM_MEDICAL_OBSERVER,
    user_template=(
        "This is a mel-spectrogram image of a child's breathing audio recorded by a phone "
        "microphone placed near the child's chest/mouth.\n\n"
        "The image shows:\n"
        "- Vertical axis: frequency (50 Hz at bottom to 4000 Hz at top)\n"
        "- Horizontal axis: time (left to right)\n"
        "- Brightness: intensity (brighter = louder)\n\n"
        "Interpret the spectrogram to classify the breath sounds:\n"
        "- Wheeze: continuous horizontal bright bands (200-1000 Hz), musical quality\n"
        "- Stridor: bright band at high frequency (500-1500 Hz), during inspiration\n"
        "- Crackles: short vertical bright spots (discontinuous, scattered)\n"
        "- Grunting: low frequency bright spots at end of expiration (50-300 Hz)\n"
        "- Normal: even, low-intensity pattern with no prominent bands or spots\n\n"
        "Report ONLY a JSON object: "
        '{{"wheeze": true/false, "stridor": true/false, "grunting": true/false, '
        '"crackles": true/false, "normal": true/false, '
        '"confidence": <0.0-1.0>, '
        '"description": "<what patterns you see in the spectrogram>"}}'
    ),
    required_variables=frozenset(),
    expected_output_format="json",
    output_schema={
        "type": "object",
        "properties": {
            "wheeze": {"type": "boolean"},
            "stridor": {"type": "boolean"},
            "grunting": {"type": "boolean"},
            "crackles": {"type": "boolean"},
            "normal": {"type": "boolean"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "description": {"type": "string"},
        },
        "required": ["wheeze", "stridor", "grunting", "crackles", "normal", "confidence"],
    },
    max_tokens=200,
    temperature=0.0,
))


# --- Binary Breath Sound Classification from Spectrogram (matches fine-tuned LoRA adapter) ---
# IMPORTANT: This prompt MUST match the training instruction in notebook 06 exactly.
# The fine-tuned model was trained on this exact instruction format.
CLASSIFY_BREATH_SOUNDS_BINARY = PromptRegistry.register(PromptTemplate(
    name="breathing.classify_breath_sounds_binary",
    version="1.0.0",
    description=(
        "Binary breath sound classification (normal vs abnormal) from spectrogram. "
        "This prompt matches the fine-tuned LoRA adapter training instruction exactly."
    ),
    system_prompt=(
        "You are Malaika, a medical spectrogram analysis assistant. "
        "Detect abnormal breath sounds (wheeze, crackles, stridor) from spectrograms. "
        "Respond ONLY with valid JSON."
    ),
    user_template=(
        "This is a mel-spectrogram of a child's breathing audio.\n"
        "Vertical: frequency (50-4000 Hz). Horizontal: time. Brightness: intensity.\n"
        "Are the breath sounds normal or abnormal?\n"
        'Respond with JSON: {{"abnormal": true/false, "confidence": 0.0-1.0, '
        '"description": "brief reason"}}'
    ),
    required_variables=frozenset(),
    expected_output_format="json",
    output_schema={
        "type": "object",
        "properties": {
            "abnormal": {"type": "boolean"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "description": {"type": "string"},
        },
        "required": ["abnormal", "confidence"],
    },
    max_tokens=200,
    temperature=0.0,
))


# --- Breath Sound Classification from Text (Whisper transcription → Gemma 4 reasoning) ---
CLASSIFY_BREATH_SOUNDS_FROM_TEXT = PromptRegistry.register(PromptTemplate(
    name="breathing.classify_breath_sounds_from_text",
    version="1.0.0",
    description=(
        "Classify breath sounds from a text description of audio "
        "(produced by Whisper transcription). Gemma 4 reasons on the "
        "description to detect wheeze, stridor, grunting, crackles."
    ),
    system_prompt=SYSTEM_MEDICAL_OBSERVER,
    user_template=(
        "A phone microphone was placed near a child's chest/mouth to record breathing sounds. "
        "An automatic speech recognition system transcribed the audio as follows:\n\n"
        "--- AUDIO TRANSCRIPTION ---\n"
        "{transcription}\n"
        "--- END TRANSCRIPTION ---\n\n"
        "Based on this transcription and description of the audio, classify the breath sounds. "
        "Note: The transcription may contain onomatopoeia, descriptions of sounds, or may be "
        "mostly silence/noise indicators. Use clinical reasoning to interpret what these sounds "
        "likely represent.\n\n"
        "Wheeze = high-pitched whistling on expiration\n"
        "Stridor = harsh, high-pitched sound on inspiration (upper airway obstruction)\n"
        "Grunting = short, low-pitched sound at end of expiration (sign of respiratory distress)\n"
        "Crackles = discontinuous popping/bubbling sounds (fluid in airways)\n\n"
        "Report ONLY a JSON object: "
        '{{"wheeze": true/false, "stridor": true/false, "grunting": true/false, '
        '"crackles": true/false, "normal": true/false, '
        '"confidence": <0.0-1.0>, '
        '"description": "<your clinical interpretation>"}}'
    ),
    required_variables=frozenset({"transcription"}),
    expected_output_format="json",
    output_schema={
        "type": "object",
        "properties": {
            "wheeze": {"type": "boolean"},
            "stridor": {"type": "boolean"},
            "grunting": {"type": "boolean"},
            "crackles": {"type": "boolean"},
            "normal": {"type": "boolean"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "description": {"type": "string"},
        },
        "required": ["wheeze", "stridor", "grunting", "crackles", "normal", "confidence"],
    },
    max_tokens=200,
    temperature=0.0,
))
