"""Tests for vision perception module — image and video analysis.

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
from malaika.types import (
    FindingStatus,
    ValidatedOutput,
)
from malaika.vision import (
    assess_alertness,
    assess_dehydration_signs,
    assess_skin_color,
    assess_wasting,
    count_breathing_rate,
    detect_chest_indrawing,
    detect_edema,
)

# Import prompts to ensure registration
from malaika.prompts import (  # noqa: F401
    breathing,
    danger_signs,
    diarrhea,
    fever,
    nutrition,
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
def temp_image(tmp_path: Path) -> Path:
    """Create a minimal JPEG file for testing."""
    img = tmp_path / "test.jpg"
    img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
    return img


@pytest.fixture
def temp_video(tmp_path: Path) -> Path:
    """Create a minimal MP4 file for testing."""
    vid = tmp_path / "test.mp4"
    vid.write_bytes(b"\x00\x00\x00\x1c" + b"ftyp" + b"\x00" * 100)
    return vid


# ---------------------------------------------------------------------------
# Alertness Assessment
# ---------------------------------------------------------------------------

class TestAssessAlertness:
    """Tests for assess_alertness."""

    def test_alert_child(self, mock_inference: MalaikaInference, temp_image: Path) -> None:
        valid_output = json.dumps({
            "alertness": "alert",
            "eyes_open": True,
            "appears_responsive": True,
            "confidence": 0.9,
            "description": "Child appears alert and responsive",
        })
        validated = ValidatedOutput(status="valid", parsed=json.loads(valid_output), raw_output=valid_output)

        with patch.object(mock_inference, "analyze_image", return_value=(valid_output, validated, 0)):
            result = assess_alertness(temp_image, mock_inference)

        assert result.is_alert is True
        assert result.is_lethargic is False
        assert result.is_unconscious is False
        assert result.confidence == 0.9
        assert result.status == FindingStatus.DETECTED

    def test_lethargic_child(self, mock_inference: MalaikaInference, temp_image: Path) -> None:
        valid_output = json.dumps({
            "alertness": "lethargic",
            "eyes_open": False,
            "appears_responsive": False,
            "confidence": 0.85,
        })
        validated = ValidatedOutput(status="valid", parsed=json.loads(valid_output), raw_output=valid_output)

        with patch.object(mock_inference, "analyze_image", return_value=(valid_output, validated, 0)):
            result = assess_alertness(temp_image, mock_inference)

        assert result.is_alert is False
        assert result.is_lethargic is True
        assert result.confidence == 0.85

    def test_unconscious_child(self, mock_inference: MalaikaInference, temp_image: Path) -> None:
        valid_output = json.dumps({
            "alertness": "unconscious",
            "eyes_open": False,
            "appears_responsive": False,
            "confidence": 0.7,
        })
        validated = ValidatedOutput(status="valid", parsed=json.loads(valid_output), raw_output=valid_output)

        with patch.object(mock_inference, "analyze_image", return_value=(valid_output, validated, 0)):
            result = assess_alertness(temp_image, mock_inference)

        assert result.is_unconscious is True

    def test_inference_failure_returns_uncertain(
        self, mock_inference: MalaikaInference, temp_image: Path,
    ) -> None:
        with patch.object(mock_inference, "analyze_image", side_effect=ModelError("OOM")):
            result = assess_alertness(temp_image, mock_inference)

        assert result.status == FindingStatus.UNCERTAIN
        assert result.confidence == 0.0

    def test_uncertain_output_status(
        self, mock_inference: MalaikaInference, temp_image: Path,
    ) -> None:
        validated = ValidatedOutput(
            status="uncertain",
            parsed={"alertness": "alert", "confidence": 0.4},
            raw_output="low confidence",
        )
        with patch.object(mock_inference, "analyze_image", return_value=("low", validated, 1)):
            result = assess_alertness(temp_image, mock_inference)

        assert result.status == FindingStatus.UNCERTAIN


# ---------------------------------------------------------------------------
# Chest Indrawing
# ---------------------------------------------------------------------------

class TestDetectChestIndrawing:
    """Tests for detect_chest_indrawing."""

    def test_indrawing_detected(self, mock_inference: MalaikaInference, temp_image: Path) -> None:
        parsed = {
            "indrawing_detected": True,
            "confidence": 0.88,
            "location": "subcostal",
            "description": "Visible subcostal indrawing",
        }
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "analyze_image", return_value=(json.dumps(parsed), validated, 0)):
            result = detect_chest_indrawing(temp_image, mock_inference)

        assert result.indrawing_detected is True
        assert result.indrawing_location == "subcostal"
        assert result.status == FindingStatus.DETECTED

    def test_no_indrawing(self, mock_inference: MalaikaInference, temp_image: Path) -> None:
        parsed = {
            "indrawing_detected": False,
            "confidence": 0.9,
            "location": "none",
            "description": "No indrawing observed",
        }
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "analyze_image", return_value=(json.dumps(parsed), validated, 0)):
            result = detect_chest_indrawing(temp_image, mock_inference)

        assert result.indrawing_detected is False
        assert result.status == FindingStatus.NOT_DETECTED

    def test_failure_returns_uncertain(
        self, mock_inference: MalaikaInference, temp_image: Path,
    ) -> None:
        with patch.object(mock_inference, "analyze_image", side_effect=Exception("fail")):
            result = detect_chest_indrawing(temp_image, mock_inference)

        assert result.status == FindingStatus.UNCERTAIN


# ---------------------------------------------------------------------------
# Skin Color
# ---------------------------------------------------------------------------

class TestAssessSkinColor:
    """Tests for assess_skin_color."""

    def test_jaundice_detected(self, mock_inference: MalaikaInference, temp_image: Path) -> None:
        parsed = {
            "jaundice_detected": True,
            "cyanosis_detected": False,
            "pallor_detected": False,
            "confidence": 0.85,
        }
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "analyze_image", return_value=(json.dumps(parsed), validated, 0)):
            result = assess_skin_color(temp_image, mock_inference)

        assert result.jaundice_detected is True
        assert result.cyanosis_detected is False
        assert result.status == FindingStatus.DETECTED

    def test_no_abnormalities(self, mock_inference: MalaikaInference, temp_image: Path) -> None:
        parsed = {
            "jaundice_detected": False,
            "cyanosis_detected": False,
            "pallor_detected": False,
            "confidence": 0.9,
        }
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "analyze_image", return_value=(json.dumps(parsed), validated, 0)):
            result = assess_skin_color(temp_image, mock_inference)

        assert result.status == FindingStatus.NOT_DETECTED


# ---------------------------------------------------------------------------
# Wasting
# ---------------------------------------------------------------------------

class TestAssessWasting:
    """Tests for assess_wasting."""

    def test_wasting_detected(self, mock_inference: MalaikaInference, temp_image: Path) -> None:
        parsed = {"visible_severe_wasting": True, "confidence": 0.8}
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "analyze_image", return_value=(json.dumps(parsed), validated, 0)):
            result = assess_wasting(temp_image, mock_inference)

        assert result.visible_wasting is True
        assert result.status == FindingStatus.DETECTED

    def test_no_wasting(self, mock_inference: MalaikaInference, temp_image: Path) -> None:
        parsed = {"visible_severe_wasting": False, "confidence": 0.95}
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "analyze_image", return_value=(json.dumps(parsed), validated, 0)):
            result = assess_wasting(temp_image, mock_inference)

        assert result.visible_wasting is False
        assert result.status == FindingStatus.NOT_DETECTED


# ---------------------------------------------------------------------------
# Edema
# ---------------------------------------------------------------------------

class TestDetectEdema:
    """Tests for detect_edema."""

    def test_bilateral_edema(self, mock_inference: MalaikaInference, temp_image: Path) -> None:
        parsed = {"edema_detected": True, "bilateral": True, "confidence": 0.9}
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "analyze_image", return_value=(json.dumps(parsed), validated, 0)):
            result = detect_edema(temp_image, mock_inference)

        assert result.edema_detected is True
        assert result.status == FindingStatus.DETECTED

    def test_unilateral_edema_not_counted(
        self, mock_inference: MalaikaInference, temp_image: Path,
    ) -> None:
        """IMCI requires bilateral — unilateral should not count."""
        parsed = {"edema_detected": True, "bilateral": False, "confidence": 0.9}
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "analyze_image", return_value=(json.dumps(parsed), validated, 0)):
            result = detect_edema(temp_image, mock_inference)

        assert result.edema_detected is False
        assert result.status == FindingStatus.NOT_DETECTED

    def test_no_edema(self, mock_inference: MalaikaInference, temp_image: Path) -> None:
        parsed = {"edema_detected": False, "bilateral": False, "confidence": 0.95}
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "analyze_image", return_value=(json.dumps(parsed), validated, 0)):
            result = detect_edema(temp_image, mock_inference)

        assert result.edema_detected is False
        assert result.status == FindingStatus.NOT_DETECTED


# ---------------------------------------------------------------------------
# Dehydration Signs
# ---------------------------------------------------------------------------

class TestAssessDehydrationSigns:
    """Tests for assess_dehydration_signs."""

    def test_sunken_eyes_and_slow_pinch(
        self, mock_inference: MalaikaInference, temp_image: Path,
    ) -> None:
        parsed = {
            "sunken_eyes": True,
            "skin_pinch_result": "goes_back_slowly",
            "general_appearance": "restless_irritable",
            "confidence": 0.8,
        }
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "analyze_image", return_value=(json.dumps(parsed), validated, 0)):
            result = assess_dehydration_signs(temp_image, mock_inference)

        assert result.sunken_eyes is True
        assert result.skin_pinch_slow is True
        assert result.skin_pinch_very_slow is False
        assert result.status == FindingStatus.DETECTED

    def test_very_slow_pinch(self, mock_inference: MalaikaInference, temp_image: Path) -> None:
        parsed = {
            "sunken_eyes": False,
            "skin_pinch_result": "goes_back_very_slowly",
            "general_appearance": "normal",
            "confidence": 0.85,
        }
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "analyze_image", return_value=(json.dumps(parsed), validated, 0)):
            result = assess_dehydration_signs(temp_image, mock_inference)

        assert result.skin_pinch_very_slow is True

    def test_no_dehydration_signs(
        self, mock_inference: MalaikaInference, temp_image: Path,
    ) -> None:
        parsed = {
            "sunken_eyes": False,
            "skin_pinch_result": "goes_back_immediately",
            "general_appearance": "normal",
            "confidence": 0.9,
        }
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "analyze_image", return_value=(json.dumps(parsed), validated, 0)):
            result = assess_dehydration_signs(temp_image, mock_inference)

        assert result.status == FindingStatus.NOT_DETECTED


# ---------------------------------------------------------------------------
# Breathing Rate
# ---------------------------------------------------------------------------

class TestCountBreathingRate:
    """Tests for count_breathing_rate."""

    def test_valid_breath_count(
        self, mock_inference: MalaikaInference, temp_video: Path,
    ) -> None:
        parsed = {"breath_count": 12, "confidence": 0.85}
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "analyze_video", return_value=(json.dumps(parsed), validated, 0)):
            result = count_breathing_rate(temp_video, mock_inference, duration_seconds=15)

        assert result.breath_count == 12
        assert result.estimated_rate_per_minute == 48  # 12 / 15 * 60
        assert result.duration_seconds == 15
        assert result.status == FindingStatus.DETECTED

    def test_high_breath_count(
        self, mock_inference: MalaikaInference, temp_video: Path,
    ) -> None:
        """Fast breathing: 15 breaths in 15 seconds = 60/min."""
        parsed = {"breath_count": 15, "confidence": 0.9}
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "analyze_video", return_value=(json.dumps(parsed), validated, 0)):
            result = count_breathing_rate(temp_video, mock_inference)

        assert result.breath_count == 15
        assert result.estimated_rate_per_minute == 60

    def test_missing_breath_count_returns_uncertain(
        self, mock_inference: MalaikaInference, temp_video: Path,
    ) -> None:
        parsed = {"confidence": 0.5, "notes": "Could not count"}
        validated = ValidatedOutput(status="valid", parsed=parsed, raw_output=json.dumps(parsed))

        with patch.object(mock_inference, "analyze_video", return_value=(json.dumps(parsed), validated, 0)):
            result = count_breathing_rate(temp_video, mock_inference)

        assert result.breath_count is None
        assert result.estimated_rate_per_minute is None
        assert result.status == FindingStatus.UNCERTAIN

    def test_inference_failure(
        self, mock_inference: MalaikaInference, temp_video: Path,
    ) -> None:
        with patch.object(mock_inference, "analyze_video", side_effect=Exception("GPU error")):
            result = count_breathing_rate(temp_video, mock_inference)

        assert result.status == FindingStatus.UNCERTAIN
        assert result.confidence == 0.0
