"""Audio perception module — breath sounds, speech, and heart sounds.

Pipeline: Audio file → Whisper (transcription) → text → Gemma 4 (reasoning).

Gemma 4 E4B does NOT support native audio input (the processor ignores the
``audios`` keyword argument). Instead, we use OpenAI Whisper-small (244 MB)
via the Transformers ``pipeline("automatic-speech-recognition")`` to
transcribe audio to text, then pass that text to Gemma 4 for clinical
reasoning.

Each function: gets prompt from PromptRegistry, transcribes audio via
Whisper, calls Gemma 4 text inference, parses JSON into typed dataclass.
On parse failure returns result with status=UNCERTAIN.

This module MUST NOT contain clinical logic or thresholds.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import structlog

from malaika.config import load_config
from malaika.inference import MalaikaInference
from malaika.prompts import PromptRegistry
from malaika.spectrogram import audio_to_spectrogram
from malaika.types import (
    BreathSoundAssessment,
    FindingStatus,
    HeartSoundAssessment,
    SpeechUnderstanding,
    ValidatedOutput,
)

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Whisper Transcriber
# ---------------------------------------------------------------------------

class WhisperTranscriber:
    """Lazy-loaded Whisper model for audio-to-text transcription.

    Uses the Transformers ``pipeline("automatic-speech-recognition")``
    with ``openai/whisper-small`` (244 MB) by default.  The model is NOT
    loaded at import time — it is loaded on first ``transcribe()`` call.

    Args:
        model_name: HuggingFace model ID for Whisper.  Defaults to the
            value from ``ModelConfig.whisper_model_name``.
    """

    def __init__(self, model_name: str | None = None) -> None:
        config = load_config()
        self._model_name: str = model_name or config.model.whisper_model_name
        self._pipeline: Any | None = None

    @property
    def model_name(self) -> str:
        """The Whisper model ID being used."""
        return self._model_name

    @property
    def is_loaded(self) -> bool:
        """Whether the Whisper model is currently loaded in memory."""
        return self._pipeline is not None

    def _load(self) -> None:
        """Load the Whisper model lazily on first use."""
        if self._pipeline is not None:
            return
        try:
            from transformers import pipeline as hf_pipeline

            logger.info("loading_whisper", model_name=self._model_name)
            self._pipeline = hf_pipeline(
                "automatic-speech-recognition",
                model=self._model_name,
            )
            logger.info("whisper_loaded", model_name=self._model_name)
        except Exception as e:
            logger.error("whisper_load_failed", error=str(e))
            raise RuntimeError(
                f"Failed to load Whisper model '{self._model_name}': {e}"
            ) from e

    def transcribe(self, audio_path: Path) -> str:
        """Transcribe an audio file to text using Whisper.

        Args:
            audio_path: Path to an audio file (WAV/MP3/OGG/FLAC).

        Returns:
            Transcribed text string.

        Raises:
            RuntimeError: If the Whisper model cannot be loaded.
            FileNotFoundError: If the audio file does not exist.
            ValueError: If the audio file cannot be processed.
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        self._load()

        try:
            result = self._pipeline(str(audio_path))
            text = result.get("text", "").strip() if isinstance(result, dict) else ""
            logger.debug(
                "whisper_transcription",
                audio_path=str(audio_path),
                text_length=len(text),
            )
            return text
        except Exception as e:
            logger.error(
                "whisper_transcription_failed",
                audio_path=str(audio_path),
                error=str(e),
            )
            raise ValueError(f"Failed to transcribe audio: {e}") from e

    def unload(self) -> None:
        """Unload the Whisper model and free memory."""
        self._pipeline = None
        logger.info("whisper_unloaded")


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
# Audio Functions — Whisper transcription → Gemma 4 text reasoning
# ---------------------------------------------------------------------------

def classify_breath_sounds_from_spectrogram(
    audio_path: Path,
    inference: MalaikaInference,
) -> BreathSoundAssessment:
    """Classify breath sounds using spectrogram image analysis.

    Pipeline: audio → mel-spectrogram PNG → Gemma 4 vision.
    This is the preferred approach — it preserves acoustic features
    that Whisper (a speech model) cannot capture for breath sounds.

    Args:
        audio_path: Path to audio file (WAV/MP3/OGG/FLAC).
        inference: Loaded MalaikaInference instance.

    Returns:
        BreathSoundAssessment with detected abnormal sounds.
    """
    input_hash = _file_hash(audio_path)

    try:
        # Step 1: Convert audio to spectrogram image
        spec_path = audio_to_spectrogram(audio_path)

        # Step 2: Analyze spectrogram via Gemma 4 vision
        prompt = PromptRegistry.get("breathing.classify_breath_sounds_from_spectrogram")
        raw_output, validated, retries = inference.analyze_image(
            spec_path, prompt, input_hash=input_hash,
        )
    except RuntimeError:
        # librosa not installed — fall through to caller
        raise
    except Exception as e:
        logger.error("spectrogram_breath_sounds_failed", error=str(e))
        return BreathSoundAssessment(
            status=FindingStatus.UNCERTAIN,
            confidence=0.0,
            description=f"Spectrogram analysis failed: {e}",
            raw_model_output="",
        )

    return _parse_breath_sound_result(raw_output, validated)


def classify_breath_sounds(
    audio_path: Path,
    inference: MalaikaInference,
    transcriber: WhisperTranscriber | None = None,
    *,
    use_spectrogram: bool = True,
) -> BreathSoundAssessment:
    """Classify breath sounds from an audio recording.

    Tries spectrogram-based vision analysis first (preferred), falls back
    to Whisper transcription + text reasoning if librosa is unavailable.

    Args:
        audio_path: Path to audio file (WAV/MP3/OGG/FLAC).
        inference: Loaded MalaikaInference instance.
        transcriber: WhisperTranscriber instance (created if not provided).
        use_spectrogram: Try spectrogram approach first (default True).

    Returns:
        BreathSoundAssessment with detected abnormal sounds.
    """
    # Try spectrogram approach first (preferred for breath sounds)
    if use_spectrogram:
        try:
            return classify_breath_sounds_from_spectrogram(audio_path, inference)
        except RuntimeError:
            logger.info("spectrogram_unavailable_falling_back_to_whisper")

    # Fallback: Whisper transcription → text reasoning
    if transcriber is None:
        transcriber = WhisperTranscriber()

    input_hash = _file_hash(audio_path)

    try:
        transcription = transcriber.transcribe(audio_path)
        if not transcription:
            transcription = "(no speech or sounds detected in audio)"

        prompt = PromptRegistry.get("breathing.classify_breath_sounds_from_text")
        raw_output, validated, retries = inference.reason(
            prompt, input_hash=input_hash,
            transcription=transcription,
        )
    except Exception as e:
        logger.error("audio_breath_sounds_failed", error=str(e))
        return BreathSoundAssessment(
            status=FindingStatus.UNCERTAIN,
            confidence=0.0,
            description=f"Analysis failed: {e}",
            raw_model_output="",
        )

    return _parse_breath_sound_result(raw_output, validated)


def _parse_breath_sound_result(
    raw_output: str,
    validated: ValidatedOutput,
) -> BreathSoundAssessment:
    """Parse validated output into BreathSoundAssessment."""
    parsed = validated.parsed
    status = _status_from_validated(validated)
    confidence = _confidence_from_parsed(parsed)

    wheeze = bool(parsed.get("wheeze", False))
    stridor = bool(parsed.get("stridor", False))
    grunting = bool(parsed.get("grunting", False))
    crackles = bool(parsed.get("crackles", False))

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
    transcriber: WhisperTranscriber | None = None,
) -> SpeechUnderstanding:
    """Understand caregiver's spoken response to a clinical question.

    Pipeline: audio → Whisper transcription → Gemma 4 text reasoning.

    Args:
        audio_path: Path to audio file (WAV/MP3/OGG/FLAC).
        inference: Loaded MalaikaInference instance.
        clinical_question: The question that was asked to the caregiver.
        transcriber: WhisperTranscriber instance (created if not provided).

    Returns:
        SpeechUnderstanding with parsed intent and entities.
    """
    if transcriber is None:
        transcriber = WhisperTranscriber()

    input_hash = _file_hash(audio_path)

    try:
        # Step 1: Transcribe audio via Whisper
        transcription = transcriber.transcribe(audio_path)
        if not transcription:
            transcription = "(no speech detected in audio)"

        # Step 2: Use Gemma 4 text reasoning on the transcription
        prompt = PromptRegistry.get("speech.understand_response_from_text")
        raw_output, validated, retries = inference.reason(
            prompt, input_hash=input_hash,
            question_asked=clinical_question,
            transcription=transcription,
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
    transcription_summary = str(parsed.get("transcription_summary", ""))
    detected_language = str(parsed.get("detected_language", ""))

    return SpeechUnderstanding(
        status=status,
        confidence=confidence,
        description=transcription_summary or _description_from_parsed(parsed),
        raw_model_output=raw_output,
        understood_text=transcription_summary,
        language_detected=detected_language,
        intent=intent,
    )


def analyze_heart_sounds(
    audio_path: Path,
    inference: MalaikaInference,
    duration_seconds: int = 10,
    transcriber: WhisperTranscriber | None = None,
) -> HeartSoundAssessment:
    """Analyze heart sounds from an audio recording.

    Pipeline: audio → Whisper transcription → Gemma 4 text reasoning.

    Args:
        audio_path: Path to audio file (WAV/MP3/OGG/FLAC).
        inference: Loaded MalaikaInference instance.
        duration_seconds: Duration of the recording in seconds.
        transcriber: WhisperTranscriber instance (created if not provided).

    Returns:
        HeartSoundAssessment with BPM estimate and abnormality detection.
    """
    if transcriber is None:
        transcriber = WhisperTranscriber()

    input_hash = _file_hash(audio_path)

    try:
        # Step 1: Transcribe audio via Whisper
        transcription = transcriber.transcribe(audio_path)
        if not transcription:
            transcription = "(no discernible sounds detected in audio)"

        # Step 2: Use Gemma 4 text reasoning on the transcription
        prompt = PromptRegistry.get("heart.analyze_sounds_from_text")
        raw_output, validated, retries = inference.reason(
            prompt, input_hash=input_hash,
            duration_seconds=duration_seconds,
            transcription=transcription,
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
