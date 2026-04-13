"""Diarrhea and dehydration assessment prompts — IMCI diarrhea module.

Covers: visual dehydration signs (sunken eyes, skin pinch) and
history taking (duration, blood in stool, frequency).
"""

from malaika.prompts.base import PromptTemplate
from malaika.prompts import PromptRegistry
from malaika.prompts.system import SYSTEM_MEDICAL_OBSERVER, SYSTEM_SPEECH_LISTENER


# --- Dehydration Signs from Image ---
ASSESS_DEHYDRATION_SIGNS = PromptRegistry.register(PromptTemplate(
    name="diarrhea.assess_dehydration_signs",
    version="1.0.0",
    description=(
        "Assess visible dehydration signs from an image of the child's face "
        "and/or abdominal skin pinch, following IMCI dehydration criteria."
    ),
    system_prompt=SYSTEM_MEDICAL_OBSERVER,
    user_template=(
        "This image shows a child being assessed for dehydration. "
        "Evaluate the following IMCI dehydration indicators:\n\n"
        "1. SUNKEN EYES: Are the child's eyes sunken compared to normal?\n"
        "2. SKIN PINCH: If an abdominal skin pinch is shown, does the skin "
        "go back very slowly (>2 seconds), slowly (1-2 seconds), or immediately?\n"
        "3. GENERAL APPEARANCE: Does the child appear restless/irritable or "
        "lethargic/unconscious?\n\n"
        "Report ONLY a JSON object:\n"
        '{{"sunken_eyes": true/false, '
        '"skin_pinch_result": "<goes_back_very_slowly|goes_back_slowly|goes_back_immediately|not_visible>", '
        '"general_appearance": "<restless_irritable|lethargic|normal>", '
        '"tears_visible": true/false, '
        '"dry_mouth_visible": true/false, '
        '"confidence": <0.0-1.0>, '
        '"description": "<what you observe>"}}'
    ),
    required_variables=frozenset(),
    expected_output_format="json",
    output_schema={
        "type": "object",
        "properties": {
            "sunken_eyes": {"type": "boolean"},
            "skin_pinch_result": {
                "type": "string",
                "enum": [
                    "goes_back_very_slowly",
                    "goes_back_slowly",
                    "goes_back_immediately",
                    "not_visible",
                ],
            },
            "general_appearance": {
                "type": "string",
                "enum": ["restless_irritable", "lethargic", "normal"],
            },
            "tears_visible": {"type": "boolean"},
            "dry_mouth_visible": {"type": "boolean"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "description": {"type": "string"},
        },
        "required": [
            "sunken_eyes",
            "skin_pinch_result",
            "general_appearance",
            "confidence",
        ],
    },
    max_tokens=200,
    temperature=0.0,
))


# --- Diarrhea History from Audio/Text ---
UNDERSTAND_HISTORY = PromptRegistry.register(PromptTemplate(
    name="diarrhea.understand_history",
    version="1.0.0",
    description=(
        "Extract diarrhea history from caregiver's spoken or text response: "
        "duration, blood in stool, frequency, and related symptoms."
    ),
    system_prompt=SYSTEM_SPEECH_LISTENER,
    user_template=(
        "The caregiver was asked about their child's diarrhea.\n\n"
        "Their response: \"{caregiver_response}\"\n\n"
        "Extract the following IMCI-relevant facts:\n"
        "- How long has the diarrhea lasted? (IMCI threshold: 14 days = persistent)\n"
        "- Is there blood in the stool? (indicates dysentery)\n"
        "- How many loose stools per day?\n"
        "- Any vomiting mentioned?\n\n"
        "Report ONLY a JSON object:\n"
        '{{"duration_days": <integer or null if not stated>, '
        '"blood_in_stool": true/false/null, '
        '"stools_per_day": <integer or null if not stated>, '
        '"vomiting_reported": true/false/null, '
        '"persistent_diarrhea": true/false, '
        '"confidence": <0.0-1.0>, '
        '"extracted_details": "<summary of what caregiver said>"}}'
    ),
    required_variables=frozenset({"caregiver_response"}),
    expected_output_format="json",
    output_schema={
        "type": "object",
        "properties": {
            "duration_days": {"type": ["integer", "null"]},
            "blood_in_stool": {"type": ["boolean", "null"]},
            "stools_per_day": {"type": ["integer", "null"]},
            "vomiting_reported": {"type": ["boolean", "null"]},
            "persistent_diarrhea": {"type": "boolean"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "extracted_details": {"type": "string"},
        },
        "required": [
            "duration_days",
            "blood_in_stool",
            "persistent_diarrhea",
            "confidence",
        ],
    },
    max_tokens=200,
    temperature=0.0,
))
