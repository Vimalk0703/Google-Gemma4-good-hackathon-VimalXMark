"""Heart sound analysis prompts — auscultation via MEMS microphone.

Covers: heart sound classification, BPM estimation, and murmur detection
from audio captured by a phone or MEMS stethoscope.
"""

from malaika.prompts import PromptRegistry
from malaika.prompts.base import PromptTemplate
from malaika.prompts.system import SYSTEM_MEDICAL_OBSERVER

# --- Heart Sound Analysis from Audio (original — kept for future native audio support) ---
ANALYZE_SOUNDS = PromptRegistry.register(
    PromptTemplate(
        name="heart.analyze_sounds",
        version="1.0.0",
        description=(
            "Analyze heart sounds from an audio recording: estimate heart rate, "
            "detect murmurs, gallops, and rhythm abnormalities."
        ),
        system_prompt=SYSTEM_MEDICAL_OBSERVER,
        user_template=(
            "This is a {duration_seconds}-second audio recording of a child's heart sounds "
            "captured by a phone microphone or MEMS stethoscope placed on the chest.\n\n"
            "Analyze the heart sounds:\n"
            "1. Count the heartbeats (S1-S2 pairs) you can identify and estimate BPM.\n"
            "2. Assess rhythm: regular or irregular?\n"
            "3. Listen for murmurs: any swooshing or blowing sounds between S1 and S2 "
            "(systolic) or between S2 and S1 (diastolic)?\n"
            "4. Listen for gallops: any extra sounds (S3 or S4)?\n"
            "5. Assess overall quality: are the heart sounds clear and audible?\n\n"
            "Normal resting heart rate for children:\n"
            "- Infant (0-12 months): 100-160 bpm\n"
            "- Toddler (1-3 years): 90-150 bpm\n"
            "- Child (3-5 years): 80-140 bpm\n\n"
            "Report ONLY a JSON object:\n"
            '{{"estimated_bpm": <integer>, '
            '"beat_count": <integer>, '
            '"rhythm": "<regular|irregular>", '
            '"murmur_detected": true/false, '
            '"murmur_timing": "<systolic|diastolic|continuous|none>", '
            '"gallop_detected": true/false, '
            '"sound_quality": "<clear|muffled|noisy>", '
            '"confidence": <0.0-1.0>, '
            '"description": "<what you hear>"}}'
        ),
        required_variables=frozenset({"duration_seconds"}),
        expected_output_format="json",
        output_schema={
            "type": "object",
            "properties": {
                "estimated_bpm": {"type": "integer"},
                "beat_count": {"type": "integer"},
                "rhythm": {
                    "type": "string",
                    "enum": ["regular", "irregular"],
                },
                "murmur_detected": {"type": "boolean"},
                "murmur_timing": {
                    "type": "string",
                    "enum": ["systolic", "diastolic", "continuous", "none"],
                },
                "gallop_detected": {"type": "boolean"},
                "sound_quality": {
                    "type": "string",
                    "enum": ["clear", "muffled", "noisy"],
                },
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "description": {"type": "string"},
            },
            "required": [
                "estimated_bpm",
                "rhythm",
                "murmur_detected",
                "sound_quality",
                "confidence",
            ],
        },
        max_tokens=200,
        temperature=0.0,
    )
)


# --- Heart Sound Analysis from Text (Whisper transcription → Gemma 4 reasoning) ---
ANALYZE_SOUNDS_FROM_TEXT = PromptRegistry.register(
    PromptTemplate(
        name="heart.analyze_sounds_from_text",
        version="1.0.0",
        description=(
            "Analyze heart sounds from a text description of audio "
            "(produced by Whisper transcription). Gemma 4 reasons on the "
            "description to estimate BPM, detect murmurs, gallops, and rhythm issues."
        ),
        system_prompt=SYSTEM_MEDICAL_OBSERVER,
        user_template=(
            "A phone microphone or MEMS stethoscope was placed on a child's chest "
            "to record heart sounds for {duration_seconds} seconds. "
            "An automatic speech recognition system transcribed the audio as follows:\n\n"
            "--- AUDIO TRANSCRIPTION ---\n"
            "{transcription}\n"
            "--- END TRANSCRIPTION ---\n\n"
            "Based on this transcription and description of the audio, analyze the heart sounds. "
            "Note: The transcription may contain onomatopoeia (lub-dub, thump-thump), "
            "descriptions of rhythmic sounds, or noise indicators. Use clinical reasoning "
            "to interpret what these sounds likely represent.\n\n"
            "Normal resting heart rate for children:\n"
            "- Infant (0-12 months): 100-160 bpm\n"
            "- Toddler (1-3 years): 90-150 bpm\n"
            "- Child (3-5 years): 80-140 bpm\n\n"
            "Report ONLY a JSON object:\n"
            '{{"estimated_bpm": <integer or null>, '
            '"rhythm": "<regular|irregular>", '
            '"murmur_detected": true/false, '
            '"murmur_timing": "<systolic|diastolic|continuous|none>", '
            '"gallop_detected": true/false, '
            '"sound_quality": "<clear|muffled|noisy>", '
            '"confidence": <0.0-1.0>, '
            '"description": "<your clinical interpretation>"}}'
        ),
        required_variables=frozenset({"duration_seconds", "transcription"}),
        expected_output_format="json",
        output_schema={
            "type": "object",
            "properties": {
                "estimated_bpm": {"type": ["integer", "null"]},
                "rhythm": {
                    "type": "string",
                    "enum": ["regular", "irregular"],
                },
                "murmur_detected": {"type": "boolean"},
                "murmur_timing": {
                    "type": "string",
                    "enum": ["systolic", "diastolic", "continuous", "none"],
                },
                "gallop_detected": {"type": "boolean"},
                "sound_quality": {
                    "type": "string",
                    "enum": ["clear", "muffled", "noisy"],
                },
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "description": {"type": "string"},
            },
            "required": [
                "rhythm",
                "murmur_detected",
                "sound_quality",
                "confidence",
            ],
        },
        max_tokens=200,
        temperature=0.0,
    )
)
