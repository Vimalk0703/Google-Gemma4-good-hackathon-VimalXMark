"""Fever assessment prompts — IMCI fever module.

Covers: fever history (duration, stiff neck, malaria risk area) and
measles sign detection (rash, mouth ulcers, eye complications).
"""

from malaika.prompts.base import PromptTemplate
from malaika.prompts import PromptRegistry
from malaika.prompts.system import SYSTEM_MEDICAL_OBSERVER, SYSTEM_SPEECH_LISTENER


# --- Fever History from Audio/Text ---
ASSESS_HISTORY = PromptRegistry.register(PromptTemplate(
    name="fever.assess_history",
    version="1.0.0",
    description=(
        "Extract fever history from caregiver's spoken or text response: "
        "duration, stiff neck reported, malaria area, and associated symptoms."
    ),
    system_prompt=SYSTEM_SPEECH_LISTENER,
    user_template=(
        "The caregiver was asked about their child's fever.\n\n"
        "Their response: \"{caregiver_response}\"\n\n"
        "Extract the following IMCI-relevant facts:\n"
        "- How long has the fever lasted? (IMCI threshold: 7 days = prolonged)\n"
        "- Has the caregiver noticed a stiff neck? (sign of meningitis)\n"
        "- Does the child live in or recently visited a malaria-risk area?\n"
        "- Any rash mentioned?\n"
        "- Any convulsions/fits mentioned?\n\n"
        "Report ONLY a JSON object:\n"
        '{{"duration_days": <integer or null if not stated>, '
        '"stiff_neck_reported": true/false/null, '
        '"malaria_risk_area": true/false/null, '
        '"rash_reported": true/false/null, '
        '"convulsions_reported": true/false/null, '
        '"prolonged_fever": true/false, '
        '"confidence": <0.0-1.0>, '
        '"extracted_details": "<summary of what caregiver said>"}}'
    ),
    required_variables=frozenset({"caregiver_response"}),
    expected_output_format="json",
    output_schema={
        "type": "object",
        "properties": {
            "duration_days": {"type": ["integer", "null"]},
            "stiff_neck_reported": {"type": ["boolean", "null"]},
            "malaria_risk_area": {"type": ["boolean", "null"]},
            "rash_reported": {"type": ["boolean", "null"]},
            "convulsions_reported": {"type": ["boolean", "null"]},
            "prolonged_fever": {"type": "boolean"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "extracted_details": {"type": "string"},
        },
        "required": [
            "duration_days",
            "stiff_neck_reported",
            "prolonged_fever",
            "confidence",
        ],
    },
    max_tokens=200,
    temperature=0.0,
))


# --- Measles Signs from Image ---
CHECK_MEASLES_SIGNS = PromptRegistry.register(PromptTemplate(
    name="fever.check_measles_signs",
    version="1.0.0",
    description=(
        "Detect measles-related signs from an image: generalised rash, "
        "mouth ulcers (Koplik spots), and eye complications."
    ),
    system_prompt=SYSTEM_MEDICAL_OBSERVER,
    user_template=(
        "This image shows a child being assessed for measles complications. "
        "Evaluate the following IMCI measles indicators:\n\n"
        "1. RASH: Is there a generalised maculopapular (non-vesicular) rash?\n"
        "2. MOUTH: Are there mouth ulcers, white spots on inner cheek "
        "(Koplik spots), or deep/extensive mouth sores?\n"
        "3. EYES: Is there pus draining from the eyes, or corneal clouding?\n\n"
        "Report ONLY a JSON object:\n"
        '{{"rash_present": true/false, '
        '"rash_type": "<maculopapular|vesicular|petechial|none>", '
        '"mouth_ulcers": true/false, '
        '"deep_extensive_mouth_sores": true/false, '
        '"eye_pus": true/false, '
        '"corneal_clouding": true/false, '
        '"confidence": <0.0-1.0>, '
        '"description": "<what you observe>"}}'
    ),
    required_variables=frozenset(),
    expected_output_format="json",
    output_schema={
        "type": "object",
        "properties": {
            "rash_present": {"type": "boolean"},
            "rash_type": {
                "type": "string",
                "enum": ["maculopapular", "vesicular", "petechial", "none"],
            },
            "mouth_ulcers": {"type": "boolean"},
            "deep_extensive_mouth_sores": {"type": "boolean"},
            "eye_pus": {"type": "boolean"},
            "corneal_clouding": {"type": "boolean"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "description": {"type": "string"},
        },
        "required": [
            "rash_present",
            "mouth_ulcers",
            "eye_pus",
            "corneal_clouding",
            "confidence",
        ],
    },
    max_tokens=200,
    temperature=0.0,
))
