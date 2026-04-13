"""Nutrition assessment prompts — IMCI malnutrition/anaemia module.

Covers: visible severe wasting and bilateral pitting edema of feet.
"""

from malaika.prompts.base import PromptTemplate
from malaika.prompts import PromptRegistry
from malaika.prompts.system import SYSTEM_MEDICAL_OBSERVER


# --- Visible Wasting from Image ---
ASSESS_WASTING = PromptRegistry.register(PromptTemplate(
    name="nutrition.assess_wasting",
    version="1.0.0",
    description=(
        "Assess visible severe wasting from an image of the child, "
        "following IMCI malnutrition criteria."
    ),
    system_prompt=SYSTEM_MEDICAL_OBSERVER,
    user_template=(
        "This image shows a child being assessed for malnutrition. "
        "Evaluate for visible severe wasting according to IMCI criteria.\n\n"
        "Look for:\n"
        "- ARMS/LEGS: Are they very thin with loose skin folds?\n"
        "- RIBS: Are ribs clearly visible/countable?\n"
        "- BUTTOCKS: Is there loss of fat (baggy pants appearance)?\n"
        "- FACE: Is the face thin with prominent cheekbones (old man face)?\n"
        "- SHOULDER: Are shoulder bones prominently visible?\n\n"
        "Visible severe wasting means the child looks very thin, like 'skin and bones'.\n\n"
        "Report ONLY a JSON object:\n"
        '{{"visible_severe_wasting": true/false, '
        '"ribs_visible": true/false, '
        '"limbs_thin": true/false, '
        '"buttock_wasting": true/false, '
        '"face_wasting": true/false, '
        '"confidence": <0.0-1.0>, '
        '"description": "<what you observe>"}}'
    ),
    required_variables=frozenset(),
    expected_output_format="json",
    output_schema={
        "type": "object",
        "properties": {
            "visible_severe_wasting": {"type": "boolean"},
            "ribs_visible": {"type": "boolean"},
            "limbs_thin": {"type": "boolean"},
            "buttock_wasting": {"type": "boolean"},
            "face_wasting": {"type": "boolean"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "description": {"type": "string"},
        },
        "required": ["visible_severe_wasting", "confidence"],
    },
    max_tokens=200,
    temperature=0.0,
))


# --- Edema Detection from Image ---
DETECT_EDEMA = PromptRegistry.register(PromptTemplate(
    name="nutrition.detect_edema",
    version="1.0.0",
    description=(
        "Detect bilateral pitting edema of both feet from an image, "
        "a sign of severe acute malnutrition (kwashiorkor)."
    ),
    system_prompt=SYSTEM_MEDICAL_OBSERVER,
    user_template=(
        "This image shows a child's feet being assessed for edema. "
        "Evaluate for bilateral pitting edema according to IMCI criteria.\n\n"
        "Pitting edema test: When you press the top of the foot with your thumb "
        "for 3 seconds and release, a dent (pit) remains.\n\n"
        "Look for:\n"
        "- SWELLING: Are both feet visibly swollen?\n"
        "- PITTING: If a thumb-press is shown, is there a visible pit/indentation?\n"
        "- BILATERAL: Is swelling present on BOTH feet? (must be bilateral for IMCI)\n\n"
        "Report ONLY a JSON object:\n"
        '{{"edema_detected": true/false, '
        '"bilateral": true/false, '
        '"pitting_visible": true/false, '
        '"left_foot_swollen": true/false, '
        '"right_foot_swollen": true/false, '
        '"confidence": <0.0-1.0>, '
        '"description": "<what you observe>"}}'
    ),
    required_variables=frozenset(),
    expected_output_format="json",
    output_schema={
        "type": "object",
        "properties": {
            "edema_detected": {"type": "boolean"},
            "bilateral": {"type": "boolean"},
            "pitting_visible": {"type": "boolean"},
            "left_foot_swollen": {"type": "boolean"},
            "right_foot_swollen": {"type": "boolean"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "description": {"type": "string"},
        },
        "required": ["edema_detected", "bilateral", "confidence"],
    },
    max_tokens=150,
    temperature=0.0,
))
