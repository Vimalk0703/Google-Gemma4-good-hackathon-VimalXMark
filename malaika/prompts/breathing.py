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


# --- Breath Sound Classification from Audio ---
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
