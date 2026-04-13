"""Speech understanding prompts — caregiver response parsing.

Covers: understanding spoken caregiver responses, extracting structured
intent and clinical entities from natural speech in any language.
"""

from malaika.prompts.base import PromptTemplate
from malaika.prompts import PromptRegistry
from malaika.prompts.system import SYSTEM_SPEECH_LISTENER


# --- Understand Caregiver's Spoken Response ---
UNDERSTAND_RESPONSE = PromptRegistry.register(PromptTemplate(
    name="speech.understand_response",
    version="1.0.0",
    description=(
        "Understand a caregiver's spoken response to a Malaika question, "
        "extracting the intent, key clinical entities, and yes/no answer if applicable."
    ),
    system_prompt=SYSTEM_SPEECH_LISTENER,
    user_template=(
        "Malaika asked the caregiver: \"{question_asked}\"\n\n"
        "The caregiver's spoken response is provided as audio.\n\n"
        "Extract the following from their response:\n"
        "1. INTENT: What is the caregiver trying to communicate?\n"
        "   - 'affirmative' = yes, agrees, confirms\n"
        "   - 'negative' = no, denies, disagrees\n"
        "   - 'informative' = providing information/details\n"
        "   - 'uncertain' = not sure, maybe, doesn't know\n"
        "   - 'request_repeat' = asking Malaika to repeat the question\n"
        "   - 'request_help' = asking for help or clarification\n"
        "   - 'unrelated' = response does not address the question\n\n"
        "2. ENTITIES: Any clinical facts mentioned (symptoms, durations, quantities).\n\n"
        "3. LANGUAGE: What language did the caregiver speak in?\n\n"
        "Report ONLY a JSON object:\n"
        '{{"intent": "<affirmative|negative|informative|uncertain|request_repeat|request_help|unrelated>", '
        '"yes_no": true/false/null, '
        '"entities": [{{\"type\": \"<symptom|duration|quantity|body_part|medication>\", \"value\": \"<extracted value>\"}}], '
        '"detected_language": "<language code, e.g. en, sw, hi>", '
        '"transcription_summary": "<brief summary of what was said>", '
        '"confidence": <0.0-1.0>}}'
    ),
    required_variables=frozenset({"question_asked"}),
    expected_output_format="json",
    output_schema={
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": [
                    "affirmative",
                    "negative",
                    "informative",
                    "uncertain",
                    "request_repeat",
                    "request_help",
                    "unrelated",
                ],
            },
            "yes_no": {"type": ["boolean", "null"]},
            "entities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": [
                                "symptom",
                                "duration",
                                "quantity",
                                "body_part",
                                "medication",
                            ],
                        },
                        "value": {"type": "string"},
                    },
                    "required": ["type", "value"],
                },
            },
            "detected_language": {"type": "string"},
            "transcription_summary": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["intent", "yes_no", "entities", "confidence"],
    },
    max_tokens=200,
    temperature=0.0,
))
