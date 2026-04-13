"""Audio perception module — breath sounds, speech, and heart sounds via Gemma 4.

Each function: gets prompt from PromptRegistry, calls inference, parses
JSON into typed dataclass. On parse failure returns result with status=UNCERTAIN.

This module MUST NOT contain clinical logic or thresholds.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import structlog

from malaika.inference import MalaikaInference
from malaika.prompts import PromptRegistry
from malaika.types import (
    BreathSoundAssessment,
    FindingStatus,
    HeartSoundAssessment,
    SpeechUnderstanding,
)

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _file_hash(path: Path) -> str:
    """Compute a short SHA-256 hash of a file for cache keying."""
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
    except OSError:
        return "file_unreadable"
    return h.hexdigest()[:16]


def _status_from_validated(validated: ValidatedOutput) -> FindingStatus:
    """Map ValidatedOutput status to FindingStatus."""
    if validated.status == "valid":
        return FindingStatus.DETECTED
    return FindingStatus.UNCERTAIN


def _confidence_from_parsed(parsed: dict) -> float:
    """Extract confidence from parsed output, default 0.0."""
    conf = parsed.get("confidence", 0.0)
    return float(conf) if isinstance(conf, (int, float)) else 0.0


def _description_from_parsed(parsed: dict) -> str:
    """Extract description from parsed output, default empty."""
    return str(parsed.get("description", ""))


# ---------------------------------------------------------------------------
# Audio Functions
# ---------------------------------------------------------------------------

def classify_breath_sounds(
    audio_path: Path,
    inference: MalaikaInference,
) -> BreathSoundAssessment:
    """Classify breath sounds from an audio recording.

    Detects wheeze, stridor, grunting, and crackles.

    Args:
        audio_path: Path to audio file (WAV/MP3/OGG/FLAC).
        inference: Loaded MalaikaInference instance.

    Returns:
        BreathSoundAssessment with detected abnormal sounds.
    """
    prompt = PromptRegistry.get("breathing.classify_breath_sounds")
    input_hash = _file_hash(audio_path)

    try:
        raw_output, validated, retries = inference.analyze_audio(
            audio_path, prompt, input_hash=input_hash,
        )
    except Exception as e:
        logger.error("audio_breath_sounds_failed", error=str(e))
        return BreathSoundAssessment(
            status=FindingStatus.UNCERTAIN,
            confidence=0.0,
            description=f"Analysis failed: {e}",
            raw_model_output="",
        )

    parsed = validated.parsed
    status = _status_from_validated(validated)
    confidence = _confidence_from_parsed(parsed)

    wheeze = bool(parsed.get("wheeze", False))
    stridor = bool(parsed.get("stridor", False))
    grunting = bool(parsed.get("grunting", False))
    crackles = bool(parsed.get("crackles", False))

    # If all sounds are normal (none detected), status is NOT_DETECTED
    has_abnormal = wheeze or stridor or grunting or crackles
    if status == FindingStatus.DETECTED and not has_abnormal:
        status = FindingStatus.NOT_DETECTED

    return BreathSoundAssessment(
        status=status,
        confidence=confidence,
        description=_description_from_parsed(parsed),
        raw_model_output=raw_output,
        wheeze=wheeze,
        stridor=stridor,
        grunting=grunting,
        crackles=crackles,
    )


def understand_speech(
    audio_path: Path,
    inference: MalaikaInference,
    clinical_question: str,
) -> SpeechUnderstanding:
    """Understand caregiver's spoken response to a clinical question.

    Args:
        audio_path: Path to audio file (WAV/MP3/OGG/FLAC).
        inference: Loaded MalaikaInference instance.
        clinical_question: The question that was asked to the caregiver.

    Returns:
        SpeechUnderstanding with parsed intent and entities.
    """
    prompt = PromptRegistry.get("speech.understand_response")
    input_hash = _file_hash(audio_path)

    try:
        raw_output, validated, retries = inference.analyze_audio(
            audio_path, prompt, input_hash=input_hash,
            question_asked=clinical_question,
        )
    except Exception as e:
        logger.error("audio_speech_understanding_failed", error=str(e))
        return SpeechUnderstanding(
            status=FindingStatus.UNCERTAIN,
            confidence=0.0,
            description=f"Analysis failed: {e}",
            raw_model_output="",
        )

    parsed = validated.parsed
    status = _status_from_validated(validated)
    confidence = _confidence_from_parsed(parsed)

    intent = str(parsed.get("intent", "uncertain"))
    transcription = str(parsed.get("transcription_summary", ""))
    detected_language = str(parsed.get("detected_language", ""))

    return SpeechUnderstanding(
        status=status,
        confidence=confidence,
        description=transcription or _description_from_parsed(parsed),
        raw_model_output=raw_output,
        understood_text=transcription,
        language_detected=detected_language,
        intent=intent,
    )


def analyze_heart_sounds(
    audio_path: Path,
    inference: MalaikaInference,
    duration_seconds: int = 10,
) -> HeartSoundAssessment:
    """Analyze heart sounds from an audio recording.

    Args:
        audio_path: Path to audio file (WAV/MP3/OGG/FLAC).
        inference: Loaded MalaikaInference instance.
        duration_seconds: Duration of the recording in seconds.

    Returns:
        HeartSoundAssessment with BPM estimate and abnormality detection.
    """
    prompt = PromptRegistry.get("heart.analyze_sounds")
    input_hash = _file_hash(audio_path)

    try:
        raw_output, validated, retries = inference.analyze_audio(
            audio_path, prompt, input_hash=input_hash,
            duration_seconds=duration_seconds,
        )
    except Exception as e:
        logger.error("audio_heart_sounds_failed", error=str(e))
        return HeartSoundAssessment(
            status=FindingStatus.UNCERTAIN,
            confidence=0.0,
            description=f"Analysis failed: {e}",
            raw_model_output="",
        )

    parsed = validated.parsed
    status = _status_from_validated(validated)
    confidence = _confidence_from_parsed(parsed)

    estimated_bpm = parsed.get("estimated_bpm")
    if isinstance(estimated_bpm, (int, float)):
        estimated_bpm = int(estimated_bpm)
    else:
        estimated_bpm = None

    murmur = bool(parsed.get("murmur_detected", False))
    gallop = bool(parsed.get("gallop_detected", False))
    rhythm = parsed.get("rhythm", "regular")
    abnormal_sounds = murmur or gallop or rhythm == "irregular"

    return HeartSoundAssessment(
        status=status,
        confidence=confidence,
        description=_description_from_parsed(parsed),
        raw_model_output=raw_output,
        estimated_bpm=estimated_bpm,
        abnormal_sounds=abnormal_sounds,
    )
