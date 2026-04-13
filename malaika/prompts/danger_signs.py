"""Danger sign assessment prompts — IMCI general danger signs.

Covers: alertness/consciousness level, ability to drink/breastfeed.
These are the FIRST checks in IMCI — any positive finding = urgent referral.
"""

from malaika.prompts.base import PromptTemplate
from malaika.prompts import PromptRegistry
from malaika.prompts.system import SYSTEM_MEDICAL_OBSERVER, SYSTEM_SPEECH_LISTENER


# --- Alertness Assessment from Image ---
ASSESS_ALERTNESS = PromptRegistry.register(PromptTemplate(
    name="danger.assess_alertness",
    version="1.0.0",
    description=(
        "Assess whether a child is alert, lethargic, or unconscious "
        "from an image, following IMCI general danger sign criteria."
    ),
    system_prompt=SYSTEM_MEDICAL_OBSERVER,
    user_template=(
        "This image shows a young child. Assess the child's level of consciousness "
        "according to WHO IMCI danger sign criteria.\n\n"
        "Look for:\n"
        "- Eyes: Are they open, tracking, or closed/unfocused?\n"
        "- Posture: Is the child sitting/moving, floppy, or rigid?\n"
        "- Responsiveness: Does the child appear aware of surroundings?\n\n"
        "A child is LETHARGIC if they are abnormally sleepy, difficult to wake, "
        "or do not look at the caregiver when spoken to.\n"
        "A child is UNCONSCIOUS if they cannot be woken at all.\n\n"
        "Report ONLY a JSON object:\n"
        '{{"alertness": "<alert|lethargic|unconscious>", '
        '"eyes_open": true/false, '
        '"appears_responsive": true/false, '
        '"muscle_tone": "<normal|floppy|rigid>", '
        '"confidence": <0.0-1.0>, '
        '"description": "<brief observation>"}}'
    ),
    required_variables=frozenset(),
    expected_output_format="json",
    output_schema={
        "type": "object",
        "properties": {
            "alertness": {
                "type": "string",
                "enum": ["alert", "lethargic", "unconscious"],
            },
            "eyes_open": {"type": "boolean"},
            "appears_responsive": {"type": "boolean"},
            "muscle_tone": {
                "type": "string",
                "enum": ["normal", "floppy", "rigid"],
            },
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "description": {"type": "string"},
        },
        "required": ["alertness", "eyes_open", "appears_responsive", "confidence"],
    },
    max_tokens=150,
    temperature=0.0,
))


# --- Skin Color Assessment from Image ---
ASSESS_SKIN_COLOR = PromptRegistry.register(PromptTemplate(
    name="danger.assess_skin_color",
    version="1.0.0",
    description=(
        "Assess skin color abnormalities from an image: jaundice (yellowing), "
        "cyanosis (blue discoloration), pallor (paleness)."
    ),
    system_prompt=SYSTEM_MEDICAL_OBSERVER,
    user_template=(
        "This image shows a young child. Assess the child's skin color for "
        "abnormalities according to WHO IMCI criteria.\n\n"
        "Look for:\n"
        "- JAUNDICE: Yellowing of the skin and/or whites of the eyes\n"
        "- CYANOSIS: Blue or grey discoloration of lips, tongue, or nail beds\n"
        "- PALLOR: Unusual paleness of palms, nail beds, or conjunctiva\n\n"
        "Consider the child's natural skin tone when assessing.\n\n"
        "Report ONLY a JSON object:\n"
        '{{"jaundice_detected": true/false, '
        '"cyanosis_detected": true/false, '
        '"pallor_detected": true/false, '
        '"confidence": <0.0-1.0>, '
        '"description": "<brief observation>"}}'
    ),
    required_variables=frozenset(),
    expected_output_format="json",
    output_schema={
        "type": "object",
        "properties": {
            "jaundice_detected": {"type": "boolean"},
            "cyanosis_detected": {"type": "boolean"},
            "pallor_detected": {"type": "boolean"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "description": {"type": "string"},
        },
        "required": ["jaundice_detected", "cyanosis_detected", "pallor_detected", "confidence"],
    },
    max_tokens=150,
    temperature=0.0,
))


# --- Ability to Drink Assessment from Audio/Text ---
CHECK_ABILITY_TO_DRINK = PromptRegistry.register(PromptTemplate(
    name="danger.check_ability_to_drink",
    version="1.0.0",
    description=(
        "Determine from caregiver's spoken or text response whether the child "
        "is able to drink or breastfeed, per IMCI danger sign criteria."
    ),
    system_prompt=SYSTEM_SPEECH_LISTENER,
    user_template=(
        "The caregiver was asked: 'Is your child able to drink or breastfeed?'\n\n"
        "Their response (transcribed or spoken): \"{caregiver_response}\"\n\n"
        "Extract whether the child can drink. According to IMCI:\n"
        "- 'Not able to drink' = child cannot swallow when offered fluid/breast\n"
        "- 'Vomits everything' = child vomits immediately after every attempt\n\n"
        "Report ONLY a JSON object:\n"
        '{{"able_to_drink": true/false, '
        '"vomits_everything": true/false, '
        '"breastfeeding_mentioned": true/false, '
        '"confidence": <0.0-1.0>, '
        '"extracted_details": "<what the caregiver said, summarised>"}}'
    ),
    required_variables=frozenset({"caregiver_response"}),
    expected_output_format="json",
    output_schema={
        "type": "object",
        "properties": {
            "able_to_drink": {"type": "boolean"},
            "vomits_everything": {"type": "boolean"},
            "breastfeeding_mentioned": {"type": "boolean"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "extracted_details": {"type": "string"},
        },
        "required": ["able_to_drink", "vomits_everything", "confidence"],
    },
    max_tokens=150,
    temperature=0.0,
))
