"""Tests for IMCI Engine — state machine orchestration.

All tests use mocked inference and perception modules (no GPU needed).
Tests state transitions, finding recording, and module skipping.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from malaika.config import MalaikaConfig, load_config
from malaika.imci_engine import IMCIEngine
from malaika.inference import MalaikaInference
from malaika.types import (
    AlertnessAssessment,
    BreathingRateResult,
    BreathSoundAssessment,
    ChestAssessment,
    ClassificationType,
    DehydrationAssessment,
    FindingStatus,
    HeartSoundAssessment,
    IMCIState,
    NutritionAssessment,
    Severity,
    ValidatedOutput,
)

# Import prompts to ensure registration
from malaika.prompts import (  # noqa: F401
    breathing,
    danger_signs,
    diarrhea,
    fever,
    heart,
    nutrition,
    speech,
    treatment,
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
def engine(mock_inference: MalaikaInference, config: MalaikaConfig) -> IMCIEngine:
    """Create an IMCI engine with mocked inference."""
    return IMCIEngine(mock_inference, config, age_months=12, language="en")


@pytest.fixture
def temp_image(tmp_path: Path) -> Path:
    img = tmp_path / "test.jpg"
    img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
    return img


@pytest.fixture
def temp_video(tmp_path: Path) -> Path:
    vid = tmp_path / "test.mp4"
    vid.write_bytes(b"\x00\x00\x00\x1c" + b"ftyp" + b"\x00" * 100)
    return vid


@pytest.fixture
def temp_audio(tmp_path: Path) -> Path:
    wav = tmp_path / "test.wav"
    wav.write_bytes(b"RIFF" + b"\x00" * 4 + b"WAVE" + b"\x00" * 100)
    return wav


# ---------------------------------------------------------------------------
# State Machine Tests
# ---------------------------------------------------------------------------

class TestStateTransitions:
    """Tests for IMCI state machine transitions."""

    def test_initial_state(self, engine: IMCIEngine) -> None:
        assert engine.current_state == IMCIState.DANGER_SIGNS
        assert not engine.is_complete

    def test_advance_follows_protocol_order(self, engine: IMCIEngine) -> None:
        """State advances in mandatory IMCI order."""
        expected_states = [
            IMCIState.BREATHING,
            IMCIState.DIARRHEA,
            IMCIState.FEVER,
            IMCIState.NUTRITION,
            # HEART_MEMS is skipped by default (enable_heart_rate=False)
            IMCIState.CLASSIFY,
            # CLASSIFY auto-runs classification
        ]

        for expected in expected_states:
            state = engine.advance()
            assert state == expected, f"Expected {expected}, got {state}"

    def test_advance_past_complete_raises(self, engine: IMCIEngine) -> None:
        """Cannot advance past COMPLETE state."""
        # Advance through all states
        while not engine.is_complete:
            # Mock treatment generation
            with patch.object(engine._inference, "reason") as mock_reason:
                mock_reason.return_value = (
                    "Treatment text",
                    ValidatedOutput(status="valid", parsed={"text": "Treatment"}, raw_output="Treatment"),
                    0,
                )
                engine.advance()

        assert engine.is_complete

        with pytest.raises(RuntimeError, match="already complete"):
            engine.advance()

    def test_heart_mems_skipped_when_disabled(self, engine: IMCIEngine) -> None:
        """HEART_MEMS should be skipped when feature flag is off."""
        # Default config has enable_heart_rate=False
        # Advance to nutrition
        for _ in range(4):  # DANGER -> BREATHING -> DIARRHEA -> FEVER -> NUTRITION
            engine.advance()

        assert engine.current_state == IMCIState.NUTRITION

        # Next advance should skip HEART_MEMS and go to CLASSIFY
        engine.advance()
        assert engine.current_state == IMCIState.CLASSIFY

    def test_heart_mems_not_skipped_when_enabled(
        self, mock_inference: MalaikaInference,
    ) -> None:
        """HEART_MEMS should NOT be skipped when feature flag is on."""
        config = load_config()
        config.features.enable_heart_rate = True
        eng = IMCIEngine(mock_inference, config, age_months=12)

        # Advance to nutrition
        for _ in range(4):
            eng.advance()

        assert eng.current_state == IMCIState.NUTRITION

        # Next should be HEART_MEMS
        eng.advance()
        assert eng.current_state == IMCIState.HEART_MEMS

    def test_session_id_exists(self, engine: IMCIEngine) -> None:
        assert engine.session_id is not None
        assert len(engine.session_id) > 0


# ---------------------------------------------------------------------------
# Danger Signs Assessment
# ---------------------------------------------------------------------------

class TestAssessDangerSigns:
    """Tests for assess_danger_signs."""

    def test_alert_child_no_danger(
        self, engine: IMCIEngine, temp_image: Path,
    ) -> None:
        alert_result = AlertnessAssessment(
            status=FindingStatus.DETECTED,
            confidence=0.9,
            description="Alert child",
            raw_model_output="",
            is_alert=True,
            is_lethargic=False,
            is_unconscious=False,
        )

        with patch("malaika.vision.assess_alertness", return_value=alert_result):
            finding = engine.assess_danger_signs(image_path=temp_image)

        assert finding.finding_status == FindingStatus.NOT_DETECTED
        assert ClassificationType.URGENT_REFERRAL not in finding.classifications

    def test_lethargic_child_triggers_danger(
        self, engine: IMCIEngine, temp_image: Path,
    ) -> None:
        lethargic_result = AlertnessAssessment(
            status=FindingStatus.DETECTED,
            confidence=0.85,
            description="Lethargic",
            raw_model_output="",
            is_alert=False,
            is_lethargic=True,
            is_unconscious=False,
        )

        with patch("malaika.vision.assess_alertness", return_value=lethargic_result):
            finding = engine.assess_danger_signs(image_path=temp_image)

        assert finding.finding_status == FindingStatus.DETECTED
        assert ClassificationType.URGENT_REFERRAL in finding.classifications

    def test_no_inputs_provided(self, engine: IMCIEngine) -> None:
        """No image or audio -> no danger signs found."""
        finding = engine.assess_danger_signs()
        assert finding.finding_status == FindingStatus.NOT_DETECTED


# ---------------------------------------------------------------------------
# Breathing Assessment
# ---------------------------------------------------------------------------

class TestAssessBreathing:
    """Tests for assess_breathing."""

    def test_fast_breathing_detected(
        self, engine: IMCIEngine, temp_video: Path, temp_image: Path, temp_audio: Path,
    ) -> None:
        br_result = BreathingRateResult(
            status=FindingStatus.DETECTED,
            confidence=0.85,
            description="Fast breathing",
            raw_model_output="",
            breath_count=14,
            duration_seconds=15,
            estimated_rate_per_minute=56,
        )
        chest_result = ChestAssessment(
            status=FindingStatus.NOT_DETECTED,
            confidence=0.9,
            description="No indrawing",
            raw_model_output="",
            indrawing_detected=False,
        )
        sound_result = BreathSoundAssessment(
            status=FindingStatus.NOT_DETECTED,
            confidence=0.9,
            description="Normal",
            raw_model_output="",
        )

        with patch("malaika.vision.count_breathing_rate", return_value=br_result), \
             patch("malaika.vision.detect_chest_indrawing", return_value=chest_result), \
             patch("malaika.audio.classify_breath_sounds", return_value=sound_result):
            finding = engine.assess_breathing(
                video_path=temp_video,
                image_path=temp_image,
                audio_path=temp_audio,
                has_cough=True,
            )

        # 56/min for 12-month child (threshold 40) = PNEUMONIA
        assert ClassificationType.PNEUMONIA in finding.classifications

    def test_severe_pneumonia_with_indrawing(
        self, engine: IMCIEngine, temp_image: Path,
    ) -> None:
        chest_result = ChestAssessment(
            status=FindingStatus.DETECTED,
            confidence=0.9,
            description="Indrawing present",
            raw_model_output="",
            indrawing_detected=True,
            indrawing_location="subcostal",
        )

        with patch("malaika.vision.detect_chest_indrawing", return_value=chest_result):
            finding = engine.assess_breathing(image_path=temp_image)

        assert ClassificationType.SEVERE_PNEUMONIA in finding.classifications

    def test_normal_breathing(self, engine: IMCIEngine) -> None:
        """No inputs -> no abnormality -> green classification."""
        finding = engine.assess_breathing()
        assert ClassificationType.NO_PNEUMONIA_COUGH_OR_COLD in finding.classifications


# ---------------------------------------------------------------------------
# Diarrhea Assessment
# ---------------------------------------------------------------------------

class TestAssessDiarrhea:
    """Tests for assess_diarrhea."""

    def test_no_diarrhea(self, engine: IMCIEngine) -> None:
        finding = engine.assess_diarrhea(has_diarrhea=False)
        assert finding.finding_status == FindingStatus.NOT_DETECTED

    def test_diarrhea_with_dehydration(
        self, engine: IMCIEngine, temp_image: Path,
    ) -> None:
        dehydration = DehydrationAssessment(
            status=FindingStatus.DETECTED,
            confidence=0.8,
            description="Sunken eyes and slow pinch",
            raw_model_output="",
            sunken_eyes=True,
            skin_pinch_slow=True,
        )

        with patch("malaika.vision.assess_dehydration_signs", return_value=dehydration):
            finding = engine.assess_diarrhea(
                image_path=temp_image,
                has_diarrhea=True,
                duration_days=3,
            )

        assert ClassificationType.SOME_DEHYDRATION in finding.classifications

    def test_dysentery(self, engine: IMCIEngine) -> None:
        finding = engine.assess_diarrhea(
            has_diarrhea=True,
            blood_in_stool=True,
        )
        assert ClassificationType.DYSENTERY in finding.classifications


# ---------------------------------------------------------------------------
# Fever Assessment
# ---------------------------------------------------------------------------

class TestAssessFever:
    """Tests for assess_fever."""

    def test_no_fever(self, engine: IMCIEngine) -> None:
        finding = engine.assess_fever(has_fever=False)
        assert finding.finding_status == FindingStatus.NOT_DETECTED

    def test_fever_with_stiff_neck(self, engine: IMCIEngine) -> None:
        finding = engine.assess_fever(has_fever=True, stiff_neck=True)
        assert ClassificationType.VERY_SEVERE_FEBRILE_DISEASE in finding.classifications

    def test_malaria_risk(self, engine: IMCIEngine) -> None:
        finding = engine.assess_fever(has_fever=True, malaria_risk=True)
        assert ClassificationType.MALARIA in finding.classifications


# ---------------------------------------------------------------------------
# Nutrition Assessment
# ---------------------------------------------------------------------------

class TestAssessNutrition:
    """Tests for assess_nutrition."""

    def test_severe_wasting(self, engine: IMCIEngine, temp_image: Path) -> None:
        wasting = NutritionAssessment(
            status=FindingStatus.DETECTED,
            confidence=0.9,
            description="Visible wasting",
            raw_model_output="",
            visible_wasting=True,
        )

        with patch("malaika.vision.assess_wasting", return_value=wasting):
            finding = engine.assess_nutrition(image_path=temp_image)

        assert ClassificationType.SEVERE_MALNUTRITION in finding.classifications

    def test_edema_detected(
        self, engine: IMCIEngine, temp_image: Path,
    ) -> None:
        edema = NutritionAssessment(
            status=FindingStatus.DETECTED,
            confidence=0.85,
            description="Bilateral edema",
            raw_model_output="",
            edema_detected=True,
        )

        with patch("malaika.vision.detect_edema", return_value=edema):
            finding = engine.assess_nutrition(feet_image_path=temp_image)

        assert ClassificationType.SEVERE_MALNUTRITION in finding.classifications

    def test_normal_nutrition(self, engine: IMCIEngine) -> None:
        finding = engine.assess_nutrition(muac_mm=150)
        assert ClassificationType.NO_MALNUTRITION in finding.classifications


# ---------------------------------------------------------------------------
# Heart Assessment
# ---------------------------------------------------------------------------

class TestAssessHeart:
    """Tests for assess_heart."""

    def test_normal_heart(self, engine: IMCIEngine, temp_audio: Path) -> None:
        heart_result = HeartSoundAssessment(
            status=FindingStatus.DETECTED,
            confidence=0.9,
            description="Normal",
            raw_model_output="",
            estimated_bpm=120,
            abnormal_sounds=False,
        )

        with patch("malaika.audio.analyze_heart_sounds", return_value=heart_result):
            finding = engine.assess_heart(audio_path=temp_audio)

        assert ClassificationType.HEART_NORMAL in finding.classifications

    def test_no_audio_input(self, engine: IMCIEngine) -> None:
        finding = engine.assess_heart()
        assert finding.finding_status == FindingStatus.NOT_ASSESSED


# ---------------------------------------------------------------------------
# Findings Collection
# ---------------------------------------------------------------------------

class TestFindingsCollection:
    """Tests for findings recording."""

    def test_findings_accumulate(
        self, engine: IMCIEngine, temp_image: Path,
    ) -> None:
        alert_result = AlertnessAssessment(
            status=FindingStatus.DETECTED,
            confidence=0.9,
            description="Alert",
            raw_model_output="",
            is_alert=True,
        )

        with patch("malaika.vision.assess_alertness", return_value=alert_result):
            engine.assess_danger_signs(image_path=temp_image)

        engine.advance()
        engine.assess_breathing()

        assert len(engine.findings) == 2
        assert engine.findings[0].imci_state == IMCIState.DANGER_SIGNS
        assert engine.findings[1].imci_state == IMCIState.BREATHING


# ---------------------------------------------------------------------------
# Full Assessment Flow
# ---------------------------------------------------------------------------

class TestFullAssessmentFlow:
    """Tests for complete assessment flow through engine."""

    def test_healthy_child_flow(
        self, mock_inference: MalaikaInference, config: MalaikaConfig,
    ) -> None:
        """Full flow for a healthy child — all green classifications."""
        eng = IMCIEngine(mock_inference, config, age_months=18, language="en")

        # Mock vision functions to return healthy results
        alert_result = AlertnessAssessment(
            status=FindingStatus.DETECTED, confidence=0.9,
            description="Alert", raw_model_output="",
            is_alert=True, is_lethargic=False, is_unconscious=False,
        )

        with patch("malaika.vision.assess_alertness", return_value=alert_result):
            eng.assess_danger_signs(image_path=Path("/fake.jpg"))

        eng.advance()
        eng.assess_breathing(has_cough=False)

        eng.advance()
        eng.assess_diarrhea(has_diarrhea=False)

        eng.advance()
        eng.assess_fever(has_fever=False)

        eng.advance()
        eng.assess_nutrition(muac_mm=150)

        # Advance to CLASSIFY (skips HEART_MEMS)
        eng.advance()
        assert eng.current_state == IMCIState.CLASSIFY

        # Advance to TREAT
        with patch.object(mock_inference, "reason") as mock_reason:
            mock_reason.return_value = (
                "No treatment needed.",
                ValidatedOutput(status="valid", parsed={"text": "Healthy"}, raw_output="Healthy"),
                0,
            )
            eng.advance()

        assert eng.current_state == IMCIState.TREAT

        # Advance to COMPLETE
        eng.advance()
        assert eng.is_complete

        result = eng.get_result()
        assert result.severity == Severity.GREEN
        assert result.age_months == 18

    def test_get_result(self, engine: IMCIEngine) -> None:
        result = engine.get_result()
        assert result.age_months == 12
        assert result.language == "en"
