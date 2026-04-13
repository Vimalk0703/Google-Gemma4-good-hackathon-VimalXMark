"""Tests for audio perception module — breath sounds, speech, heart sounds.

All tests use mocked inference (no GPU needed).
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
    analyze_heart_sounds,
    classify_breath_sounds,
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
def temp_audio(tmp_path: Path) -> Path:
    """Create a minimal WAV file for testing."""
    wav = tmp_path / "test.wav"
    # RIFF....WAVEfmt header (minimal)
    wav.write_bytes(b"RIFF" + b"\x00" * 4 + b"WAVE" + b"\x00" * 100)
    return wav


# ---------------------------------------------------------------------------
# Breath Sounds
# ---------------------------------------------------------------------------

class TestClassifyBreathSounds:
    """Tests for classify_breath_sounds."""

    def test_normal_breathing(self, mock_inference: MalaikaInference, temp_audio: Path) -> None:
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

        with patch.object(mock_inference, "analyze_audio", return_value=(json.dumps(parsed), validated, 0)):
            result = classify_breath_sounds(temp_audio, mock_inference)

        assert result.wheeze is False
        assert result.stridor is False
        assert result.grunting is False
        assert result.crackles is False
        assert result.status == FindingStatus.NOT_DETECTED
        assert result.confidence == 0.9

    def test_wheeze_detected(self, mock_inference: MalaikaInference, temp_audio: Path) -> None:
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

        with patch.object(mock_inference, "analyze_audio", return_value=(json.dumps(parsed), validated, 0)):
            result = classify_breath_sounds(temp_audio, mock_inference)

        assert result.wheeze is True
        assert result.status == FindingStatus.DETECTED

    def test_stridor_detected(self, mock_inference: MalaikaInference, temp_audio: Path) -> None:
        parsed = {
            "wheeze": False,
            "stridor": True,
            "grunting": False,
            "crackles": False,
            "normal": False,
            "confidence": 0.8,
        }
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "analyze_audio", return_value=(json.dumps(parsed), validated, 0)):
            result = classify_breath_sounds(temp_audio, mock_inference)

        assert result.stridor is True
        assert result.status == FindingStatus.DETECTED

    def test_multiple_abnormal_sounds(
        self, mock_inference: MalaikaInference, temp_audio: Path,
    ) -> None:
        parsed = {
            "wheeze": True,
            "stridor": True,
            "grunting": True,
            "crackles": True,
            "normal": False,
            "confidence": 0.7,
        }
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "analyze_audio", return_value=(json.dumps(parsed), validated, 0)):
            result = classify_breath_sounds(temp_audio, mock_inference)

        assert result.wheeze is True
        assert result.stridor is True
        assert result.grunting is True
        assert result.crackles is True

    def test_inference_failure_returns_uncertain(
        self, mock_inference: MalaikaInference, temp_audio: Path,
    ) -> None:
        with patch.object(mock_inference, "analyze_audio", side_effect=ModelError("fail")):
            result = classify_breath_sounds(temp_audio, mock_inference)

        assert result.status == FindingStatus.UNCERTAIN
        assert result.confidence == 0.0

    def test_uncertain_output(
        self, mock_inference: MalaikaInference, temp_audio: Path,
    ) -> None:
        validated = ValidatedOutput(
            status="uncertain",
            parsed={"wheeze": False, "stridor": False, "grunting": False, "crackles": False, "confidence": 0.3},
            raw_output="low confidence",
        )
        with patch.object(mock_inference, "analyze_audio", return_value=("low", validated, 1)):
            result = classify_breath_sounds(temp_audio, mock_inference)

        assert result.status == FindingStatus.UNCERTAIN


# ---------------------------------------------------------------------------
# Speech Understanding
# ---------------------------------------------------------------------------

class TestUnderstandSpeech:
    """Tests for understand_speech."""

    def test_affirmative_response(
        self, mock_inference: MalaikaInference, temp_audio: Path,
    ) -> None:
        parsed = {
            "intent": "affirmative",
            "yes_no": True,
            "entities": [],
            "detected_language": "en",
            "transcription_summary": "Yes, the child has been coughing for 3 days",
            "confidence": 0.9,
        }
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "analyze_audio", return_value=(json.dumps(parsed), validated, 0)):
            result = understand_speech(temp_audio, mock_inference, "Does the child have a cough?")

        assert result.intent == "affirmative"
        assert result.language_detected == "en"
        assert "coughing" in result.understood_text
        assert result.status == FindingStatus.DETECTED

    def test_negative_response(
        self, mock_inference: MalaikaInference, temp_audio: Path,
    ) -> None:
        parsed = {
            "intent": "negative",
            "yes_no": False,
            "entities": [],
            "detected_language": "sw",
            "transcription_summary": "No diarrhea",
            "confidence": 0.85,
        }
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "analyze_audio", return_value=(json.dumps(parsed), validated, 0)):
            result = understand_speech(temp_audio, mock_inference, "Does the child have diarrhea?")

        assert result.intent == "negative"
        assert result.language_detected == "sw"

    def test_uncertain_intent(
        self, mock_inference: MalaikaInference, temp_audio: Path,
    ) -> None:
        parsed = {
            "intent": "uncertain",
            "yes_no": None,
            "entities": [],
            "confidence": 0.4,
        }
        validated = ValidatedOutput(status="uncertain", parsed=parsed, raw_output="")

        with patch.object(mock_inference, "analyze_audio", return_value=("", validated, 0)):
            result = understand_speech(temp_audio, mock_inference, "Is there blood in the stool?")

        assert result.status == FindingStatus.UNCERTAIN

    def test_inference_failure(
        self, mock_inference: MalaikaInference, temp_audio: Path,
    ) -> None:
        with patch.object(mock_inference, "analyze_audio", side_effect=Exception("audio error")):
            result = understand_speech(temp_audio, mock_inference, "question?")

        assert result.status == FindingStatus.UNCERTAIN


# ---------------------------------------------------------------------------
# Heart Sounds
# ---------------------------------------------------------------------------

class TestAnalyzeHeartSounds:
    """Tests for analyze_heart_sounds."""

    def test_normal_heart(self, mock_inference: MalaikaInference, temp_audio: Path) -> None:
        parsed = {
            "estimated_bpm": 120,
            "rhythm": "regular",
            "murmur_detected": False,
            "gallop_detected": False,
            "sound_quality": "clear",
            "confidence": 0.9,
        }
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "analyze_audio", return_value=(json.dumps(parsed), validated, 0)):
            result = analyze_heart_sounds(temp_audio, mock_inference)

        assert result.estimated_bpm == 120
        assert result.abnormal_sounds is False
        assert result.status == FindingStatus.DETECTED

    def test_murmur_detected(self, mock_inference: MalaikaInference, temp_audio: Path) -> None:
        parsed = {
            "estimated_bpm": 130,
            "rhythm": "regular",
            "murmur_detected": True,
            "gallop_detected": False,
            "sound_quality": "clear",
            "confidence": 0.8,
        }
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "analyze_audio", return_value=(json.dumps(parsed), validated, 0)):
            result = analyze_heart_sounds(temp_audio, mock_inference)

        assert result.abnormal_sounds is True

    def test_irregular_rhythm(self, mock_inference: MalaikaInference, temp_audio: Path) -> None:
        parsed = {
            "estimated_bpm": 110,
            "rhythm": "irregular",
            "murmur_detected": False,
            "gallop_detected": False,
            "sound_quality": "clear",
            "confidence": 0.75,
        }
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "analyze_audio", return_value=(json.dumps(parsed), validated, 0)):
            result = analyze_heart_sounds(temp_audio, mock_inference)

        assert result.abnormal_sounds is True

    def test_no_bpm_returns_none(
        self, mock_inference: MalaikaInference, temp_audio: Path,
    ) -> None:
        parsed = {
            "rhythm": "regular",
            "murmur_detected": False,
            "sound_quality": "noisy",
            "confidence": 0.6,
        }
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "analyze_audio", return_value=(json.dumps(parsed), validated, 0)):
            result = analyze_heart_sounds(temp_audio, mock_inference)

        assert result.estimated_bpm is None

    def test_inference_failure(
        self, mock_inference: MalaikaInference, temp_audio: Path,
    ) -> None:
        with patch.object(mock_inference, "analyze_audio", side_effect=Exception("fail")):
            result = analyze_heart_sounds(temp_audio, mock_inference)

        assert result.status == FindingStatus.UNCERTAIN
        assert result.confidence == 0.0
