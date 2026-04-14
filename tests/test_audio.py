"""Tests for audio perception module — breath sounds, speech, heart sounds.

All tests use mocked inference and mocked WhisperTranscriber (no GPU or
Whisper model needed). Tests verify the Whisper→Gemma 4 text pipeline.

Tests JSON parsing: valid output, invalid output, and uncertain results.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from malaika.config import MalaikaConfig, load_config
from malaika.inference import MalaikaInference, ModelError
from malaika.types import FindingStatus, ValidatedOutput
from malaika.audio import (
    WhisperTranscriber,
    analyze_heart_sounds,
    classify_breath_sounds,
    classify_breath_sounds_from_spectrogram,
    understand_speech,
)

# Import prompts to ensure registration
from malaika.prompts import (  # noqa: F401
    breathing,
    heart,
    speech,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def config() -> MalaikaConfig:
    return load_config()


@pytest.fixture
def mock_inference(config: MalaikaConfig) -> MalaikaInference:
    inf = MalaikaInference(config)
    inf._model_loaded = True
    inf._model = MagicMock()
    inf._processor = MagicMock()
    return inf


@pytest.fixture
def mock_transcriber() -> WhisperTranscriber:
    """Create a WhisperTranscriber with mocked pipeline."""
    transcriber = WhisperTranscriber.__new__(WhisperTranscriber)
    transcriber._model_name = "openai/whisper-small"
    transcriber._pipeline = MagicMock()
    return transcriber


@pytest.fixture
def temp_audio(tmp_path: Path) -> Path:
    """Create a minimal WAV file for testing."""
    wav = tmp_path / "test.wav"
    # RIFF....WAVEfmt header (minimal)
    wav.write_bytes(b"RIFF" + b"\x00" * 4 + b"WAVE" + b"\x00" * 100)
    return wav


# ---------------------------------------------------------------------------
# WhisperTranscriber Tests
# ---------------------------------------------------------------------------

class TestWhisperTranscriber:
    """Tests for WhisperTranscriber class."""

    def test_lazy_loading(self) -> None:
        """Whisper model should NOT be loaded at construction time."""
        transcriber = WhisperTranscriber.__new__(WhisperTranscriber)
        transcriber._model_name = "openai/whisper-small"
        transcriber._pipeline = None
        assert transcriber.is_loaded is False

    def test_model_name_from_config(self) -> None:
        """Model name should default from config."""
        with patch("malaika.audio.load_config") as mock_config:
            mock_cfg = MagicMock()
            mock_cfg.model.whisper_model_name = "openai/whisper-small"
            mock_config.return_value = mock_cfg
            transcriber = WhisperTranscriber()
            assert transcriber.model_name == "openai/whisper-small"

    def test_custom_model_name(self) -> None:
        """Should accept a custom model name."""
        with patch("malaika.audio.load_config"):
            transcriber = WhisperTranscriber(model_name="openai/whisper-tiny")
            assert transcriber.model_name == "openai/whisper-tiny"

    def test_transcribe_returns_text(
        self, mock_transcriber: WhisperTranscriber, temp_audio: Path,
    ) -> None:
        """Transcribe should return text from Whisper pipeline."""
        mock_transcriber._pipeline.return_value = {"text": "the child is coughing"}
        result = mock_transcriber.transcribe(temp_audio)
        assert result == "the child is coughing"

    def test_transcribe_file_not_found(
        self, mock_transcriber: WhisperTranscriber,
    ) -> None:
        """Transcribe should raise FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError):
            mock_transcriber.transcribe(Path("/nonexistent/audio.wav"))

    def test_transcribe_empty_result(
        self, mock_transcriber: WhisperTranscriber, temp_audio: Path,
    ) -> None:
        """Transcribe should return empty string for empty Whisper output."""
        mock_transcriber._pipeline.return_value = {"text": ""}
        result = mock_transcriber.transcribe(temp_audio)
        assert result == ""

    def test_unload(self, mock_transcriber: WhisperTranscriber) -> None:
        """Unload should clear the pipeline."""
        assert mock_transcriber.is_loaded is True
        mock_transcriber.unload()
        assert mock_transcriber.is_loaded is False


# ---------------------------------------------------------------------------
# Breath Sounds
# ---------------------------------------------------------------------------

class TestClassifyBreathSounds:
    """Tests for classify_breath_sounds (Whisper → Gemma 4 text pipeline)."""

    def test_normal_breathing(
        self,
        mock_inference: MalaikaInference,
        mock_transcriber: WhisperTranscriber,
        temp_audio: Path,
    ) -> None:
        mock_transcriber._pipeline.return_value = {"text": "quiet breathing sounds"}
        parsed = {
            "wheeze": False,
            "stridor": False,
            "grunting": False,
            "crackles": False,
            "normal": True,
            "confidence": 0.9,
            "description": "Normal breath sounds",
        }
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "reason", return_value=(json.dumps(parsed), validated, 0)):
            result = classify_breath_sounds(temp_audio, mock_inference, transcriber=mock_transcriber)

        assert result.wheeze is False
        assert result.stridor is False
        assert result.grunting is False
        assert result.crackles is False
        assert result.status == FindingStatus.NOT_DETECTED
        assert result.confidence == 0.9

    def test_wheeze_detected(
        self,
        mock_inference: MalaikaInference,
        mock_transcriber: WhisperTranscriber,
        temp_audio: Path,
    ) -> None:
        mock_transcriber._pipeline.return_value = {"text": "whistling breathing sound"}
        parsed = {
            "wheeze": True,
            "stridor": False,
            "grunting": False,
            "crackles": False,
            "normal": False,
            "confidence": 0.85,
            "description": "Expiratory wheeze heard",
        }
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "reason", return_value=(json.dumps(parsed), validated, 0)):
            result = classify_breath_sounds(temp_audio, mock_inference, transcriber=mock_transcriber)

        assert result.wheeze is True
        assert result.status == FindingStatus.DETECTED

    def test_stridor_detected(
        self,
        mock_inference: MalaikaInference,
        mock_transcriber: WhisperTranscriber,
        temp_audio: Path,
    ) -> None:
        mock_transcriber._pipeline.return_value = {"text": "harsh inspiratory noise"}
        parsed = {
            "wheeze": False,
            "stridor": True,
            "grunting": False,
            "crackles": False,
            "normal": False,
            "confidence": 0.8,
        }
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "reason", return_value=(json.dumps(parsed), validated, 0)):
            result = classify_breath_sounds(temp_audio, mock_inference, transcriber=mock_transcriber)

        assert result.stridor is True
        assert result.status == FindingStatus.DETECTED

    def test_multiple_abnormal_sounds(
        self,
        mock_inference: MalaikaInference,
        mock_transcriber: WhisperTranscriber,
        temp_audio: Path,
    ) -> None:
        mock_transcriber._pipeline.return_value = {"text": "wheezing grunting crackles"}
        parsed = {
            "wheeze": True,
            "stridor": True,
            "grunting": True,
            "crackles": True,
            "normal": False,
            "confidence": 0.7,
        }
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "reason", return_value=(json.dumps(parsed), validated, 0)):
            result = classify_breath_sounds(temp_audio, mock_inference, transcriber=mock_transcriber)

        assert result.wheeze is True
        assert result.stridor is True
        assert result.grunting is True
        assert result.crackles is True

    def test_inference_failure_returns_uncertain(
        self,
        mock_inference: MalaikaInference,
        mock_transcriber: WhisperTranscriber,
        temp_audio: Path,
    ) -> None:
        mock_transcriber._pipeline.return_value = {"text": "some audio"}
        with patch.object(mock_inference, "reason", side_effect=ModelError("fail")):
            result = classify_breath_sounds(temp_audio, mock_inference, transcriber=mock_transcriber)

        assert result.status == FindingStatus.UNCERTAIN
        assert result.confidence == 0.0

    def test_whisper_failure_returns_uncertain(
        self,
        mock_inference: MalaikaInference,
        mock_transcriber: WhisperTranscriber,
        temp_audio: Path,
    ) -> None:
        mock_transcriber._pipeline.side_effect = RuntimeError("Whisper crashed")
        result = classify_breath_sounds(temp_audio, mock_inference, transcriber=mock_transcriber)

        assert result.status == FindingStatus.UNCERTAIN
        assert result.confidence == 0.0

    def test_uncertain_output(
        self,
        mock_inference: MalaikaInference,
        mock_transcriber: WhisperTranscriber,
        temp_audio: Path,
    ) -> None:
        mock_transcriber._pipeline.return_value = {"text": "unclear audio"}
        validated = ValidatedOutput(
            status="uncertain",
            parsed={"wheeze": False, "stridor": False, "grunting": False, "crackles": False, "confidence": 0.3},
            raw_output="low confidence",
        )
        with patch.object(mock_inference, "reason", return_value=("low", validated, 1)):
            result = classify_breath_sounds(temp_audio, mock_inference, transcriber=mock_transcriber)

        assert result.status == FindingStatus.UNCERTAIN

    def test_empty_transcription_uses_fallback(
        self,
        mock_inference: MalaikaInference,
        mock_transcriber: WhisperTranscriber,
        temp_audio: Path,
    ) -> None:
        """When Whisper returns empty text, a fallback placeholder is used."""
        mock_transcriber._pipeline.return_value = {"text": ""}
        parsed = {
            "wheeze": False, "stridor": False, "grunting": False,
            "crackles": False, "normal": True, "confidence": 0.5,
        }
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "reason", return_value=(json.dumps(parsed), validated, 0)) as mock_reason:
            classify_breath_sounds(temp_audio, mock_inference, transcriber=mock_transcriber)

        # Verify the fallback text was passed
        call_kwargs = mock_reason.call_args
        assert "no speech or sounds detected" in call_kwargs.kwargs.get("transcription", "")


# ---------------------------------------------------------------------------
# Speech Understanding
# ---------------------------------------------------------------------------

class TestUnderstandSpeech:
    """Tests for understand_speech (Whisper → Gemma 4 text pipeline)."""

    def test_affirmative_response(
        self,
        mock_inference: MalaikaInference,
        mock_transcriber: WhisperTranscriber,
        temp_audio: Path,
    ) -> None:
        mock_transcriber._pipeline.return_value = {
            "text": "Yes, the child has been coughing for 3 days",
        }
        parsed = {
            "intent": "affirmative",
            "yes_no": True,
            "entities": [],
            "detected_language": "en",
            "transcription_summary": "Yes, the child has been coughing for 3 days",
            "confidence": 0.9,
        }
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "reason", return_value=(json.dumps(parsed), validated, 0)):
            result = understand_speech(
                temp_audio, mock_inference, "Does the child have a cough?",
                transcriber=mock_transcriber,
            )

        assert result.intent == "affirmative"
        assert result.language_detected == "en"
        assert "coughing" in result.understood_text
        assert result.status == FindingStatus.DETECTED

    def test_negative_response(
        self,
        mock_inference: MalaikaInference,
        mock_transcriber: WhisperTranscriber,
        temp_audio: Path,
    ) -> None:
        mock_transcriber._pipeline.return_value = {"text": "Hapana, hakuna kuhara"}
        parsed = {
            "intent": "negative",
            "yes_no": False,
            "entities": [],
            "detected_language": "sw",
            "transcription_summary": "No diarrhea",
            "confidence": 0.85,
        }
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "reason", return_value=(json.dumps(parsed), validated, 0)):
            result = understand_speech(
                temp_audio, mock_inference, "Does the child have diarrhea?",
                transcriber=mock_transcriber,
            )

        assert result.intent == "negative"
        assert result.language_detected == "sw"

    def test_uncertain_intent(
        self,
        mock_inference: MalaikaInference,
        mock_transcriber: WhisperTranscriber,
        temp_audio: Path,
    ) -> None:
        mock_transcriber._pipeline.return_value = {"text": "mmm maybe"}
        parsed = {
            "intent": "uncertain",
            "yes_no": None,
            "entities": [],
            "confidence": 0.4,
        }
        validated = ValidatedOutput(status="uncertain", parsed=parsed, raw_output="")

        with patch.object(mock_inference, "reason", return_value=("", validated, 0)):
            result = understand_speech(
                temp_audio, mock_inference, "Is there blood in the stool?",
                transcriber=mock_transcriber,
            )

        assert result.status == FindingStatus.UNCERTAIN

    def test_inference_failure(
        self,
        mock_inference: MalaikaInference,
        mock_transcriber: WhisperTranscriber,
        temp_audio: Path,
    ) -> None:
        mock_transcriber._pipeline.return_value = {"text": "some speech"}
        with patch.object(mock_inference, "reason", side_effect=Exception("audio error")):
            result = understand_speech(
                temp_audio, mock_inference, "question?",
                transcriber=mock_transcriber,
            )

        assert result.status == FindingStatus.UNCERTAIN

    def test_whisper_failure_returns_uncertain(
        self,
        mock_inference: MalaikaInference,
        mock_transcriber: WhisperTranscriber,
        temp_audio: Path,
    ) -> None:
        mock_transcriber._pipeline.side_effect = RuntimeError("Whisper failed")
        result = understand_speech(
            temp_audio, mock_inference, "Has the child vomited?",
            transcriber=mock_transcriber,
        )

        assert result.status == FindingStatus.UNCERTAIN
        assert result.confidence == 0.0


# ---------------------------------------------------------------------------
# Heart Sounds
# ---------------------------------------------------------------------------

class TestAnalyzeHeartSounds:
    """Tests for analyze_heart_sounds (Whisper → Gemma 4 text pipeline)."""

    def test_normal_heart(
        self,
        mock_inference: MalaikaInference,
        mock_transcriber: WhisperTranscriber,
        temp_audio: Path,
    ) -> None:
        mock_transcriber._pipeline.return_value = {"text": "lub dub lub dub regular rhythm"}
        parsed = {
            "estimated_bpm": 120,
            "rhythm": "regular",
            "murmur_detected": False,
            "gallop_detected": False,
            "sound_quality": "clear",
            "confidence": 0.9,
        }
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "reason", return_value=(json.dumps(parsed), validated, 0)):
            result = analyze_heart_sounds(temp_audio, mock_inference, transcriber=mock_transcriber)

        assert result.estimated_bpm == 120
        assert result.abnormal_sounds is False
        assert result.status == FindingStatus.DETECTED

    def test_murmur_detected(
        self,
        mock_inference: MalaikaInference,
        mock_transcriber: WhisperTranscriber,
        temp_audio: Path,
    ) -> None:
        mock_transcriber._pipeline.return_value = {"text": "swooshing sound between beats"}
        parsed = {
            "estimated_bpm": 130,
            "rhythm": "regular",
            "murmur_detected": True,
            "gallop_detected": False,
            "sound_quality": "clear",
            "confidence": 0.8,
        }
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "reason", return_value=(json.dumps(parsed), validated, 0)):
            result = analyze_heart_sounds(temp_audio, mock_inference, transcriber=mock_transcriber)

        assert result.abnormal_sounds is True

    def test_irregular_rhythm(
        self,
        mock_inference: MalaikaInference,
        mock_transcriber: WhisperTranscriber,
        temp_audio: Path,
    ) -> None:
        mock_transcriber._pipeline.return_value = {"text": "irregular thumping"}
        parsed = {
            "estimated_bpm": 110,
            "rhythm": "irregular",
            "murmur_detected": False,
            "gallop_detected": False,
            "sound_quality": "clear",
            "confidence": 0.75,
        }
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "reason", return_value=(json.dumps(parsed), validated, 0)):
            result = analyze_heart_sounds(temp_audio, mock_inference, transcriber=mock_transcriber)

        assert result.abnormal_sounds is True

    def test_no_bpm_returns_none(
        self,
        mock_inference: MalaikaInference,
        mock_transcriber: WhisperTranscriber,
        temp_audio: Path,
    ) -> None:
        mock_transcriber._pipeline.return_value = {"text": "noisy recording"}
        parsed = {
            "rhythm": "regular",
            "murmur_detected": False,
            "sound_quality": "noisy",
            "confidence": 0.6,
        }
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "reason", return_value=(json.dumps(parsed), validated, 0)):
            result = analyze_heart_sounds(temp_audio, mock_inference, transcriber=mock_transcriber)

        assert result.estimated_bpm is None

    def test_inference_failure(
        self,
        mock_inference: MalaikaInference,
        mock_transcriber: WhisperTranscriber,
        temp_audio: Path,
    ) -> None:
        mock_transcriber._pipeline.return_value = {"text": "some audio"}
        with patch.object(mock_inference, "reason", side_effect=Exception("fail")):
            result = analyze_heart_sounds(temp_audio, mock_inference, transcriber=mock_transcriber)

        assert result.status == FindingStatus.UNCERTAIN
        assert result.confidence == 0.0

    def test_whisper_failure_returns_uncertain(
        self,
        mock_inference: MalaikaInference,
        mock_transcriber: WhisperTranscriber,
        temp_audio: Path,
    ) -> None:
        mock_transcriber._pipeline.side_effect = RuntimeError("Whisper crashed")
        result = analyze_heart_sounds(temp_audio, mock_inference, transcriber=mock_transcriber)

        assert result.status == FindingStatus.UNCERTAIN
        assert result.confidence == 0.0


# ---------------------------------------------------------------------------
# Spectrogram-Based Breath Sounds
# ---------------------------------------------------------------------------

class TestSpectrogramBreathSounds:
    """Tests for spectrogram-based breath sound classification."""

    def test_spectrogram_fallback_to_whisper(
        self,
        mock_inference: MalaikaInference,
        mock_transcriber: WhisperTranscriber,
        temp_audio: Path,
    ) -> None:
        """When librosa is unavailable, classify_breath_sounds falls back to Whisper."""
        mock_transcriber._pipeline.return_value = {"text": "quiet breathing"}
        parsed = {
            "wheeze": False, "stridor": False, "grunting": False,
            "crackles": False, "normal": True, "confidence": 0.8,
        }
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "reason", return_value=(json.dumps(parsed), validated, 0)):
            with patch("malaika.audio.audio_to_spectrogram", side_effect=RuntimeError("no librosa")):
                result = classify_breath_sounds(
                    temp_audio, mock_inference, transcriber=mock_transcriber,
                    use_spectrogram=True,
                )

        assert result.status == FindingStatus.NOT_DETECTED
        assert result.confidence == 0.8

    def test_spectrogram_disabled(
        self,
        mock_inference: MalaikaInference,
        mock_transcriber: WhisperTranscriber,
        temp_audio: Path,
    ) -> None:
        """When use_spectrogram=False, should skip spectrogram entirely."""
        mock_transcriber._pipeline.return_value = {"text": "wheezing"}
        parsed = {
            "wheeze": True, "stridor": False, "grunting": False,
            "crackles": False, "normal": False, "confidence": 0.9,
        }
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "reason", return_value=(json.dumps(parsed), validated, 0)):
            result = classify_breath_sounds(
                temp_audio, mock_inference, transcriber=mock_transcriber,
                use_spectrogram=False,
            )

        assert result.wheeze is True
        assert result.status == FindingStatus.DETECTED

    def test_spectrogram_direct_success(
        self,
        mock_inference: MalaikaInference,
        temp_audio: Path,
        tmp_path: Path,
    ) -> None:
        """classify_breath_sounds_from_spectrogram with mocked spectrogram generation."""
        spec_path = tmp_path / "spec.png"
        spec_path.write_bytes(b"fake png")

        parsed = {
            "wheeze": True, "stridor": False, "grunting": False,
            "crackles": True, "normal": False, "confidence": 0.85,
            "description": "Wheeze and crackles in spectrogram",
        }
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch("malaika.audio.audio_to_spectrogram", return_value=spec_path):
            with patch.object(
                mock_inference, "analyze_image",
                return_value=(json.dumps(parsed), validated, 0),
            ):
                result = classify_breath_sounds_from_spectrogram(temp_audio, mock_inference)

        assert result.wheeze is True
        assert result.crackles is True
        assert result.status == FindingStatus.DETECTED
        assert result.confidence == 0.85

    def test_spectrogram_direct_failure(
        self,
        mock_inference: MalaikaInference,
        temp_audio: Path,
        tmp_path: Path,
    ) -> None:
        """classify_breath_sounds_from_spectrogram returns UNCERTAIN on non-RuntimeError."""
        with patch("malaika.audio.audio_to_spectrogram", side_effect=ValueError("bad audio")):
            result = classify_breath_sounds_from_spectrogram(temp_audio, mock_inference)

        assert result.status == FindingStatus.UNCERTAIN
        assert result.confidence == 0.0

    def test_spectrogram_direct_librosa_missing(
        self,
        mock_inference: MalaikaInference,
        temp_audio: Path,
    ) -> None:
        """classify_breath_sounds_from_spectrogram propagates RuntimeError."""
        with patch("malaika.audio.audio_to_spectrogram", side_effect=RuntimeError("no librosa")):
            with pytest.raises(RuntimeError):
                classify_breath_sounds_from_spectrogram(temp_audio, mock_inference)
