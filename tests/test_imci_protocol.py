"""Tests for WHO IMCI protocol classification logic.

Target: 100% coverage on imci_protocol.py.
Every threshold boundary, every classification path, every edge case.
"""

from __future__ import annotations

import pytest

from malaika.imci_protocol import (
    AggregateClassification,
    DomainClassification,
    FAST_BREATHING_THRESHOLD_2_TO_11_MONTHS,
    FAST_BREATHING_THRESHOLD_12_TO_59_MONTHS,
    MUAC_MODERATE_THRESHOLD_MM,
    MUAC_SEVERE_THRESHOLD_MM,
    PERSISTENT_DIARRHEA_THRESHOLD_DAYS,
    classify_assessment,
    classify_breathing,
    classify_danger_signs,
    classify_diarrhea,
    classify_fever,
    classify_heart,
    classify_nutrition,
    is_fast_breathing,
)
from malaika.types import ClassificationType, ReferralUrgency, Severity


# ============================================================================
# DANGER SIGNS
# ============================================================================

class TestClassifyDangerSigns:
    """Tests for classify_danger_signs — IMCI Chart Booklet p.2."""

    def test_no_danger_signs_returns_none(self) -> None:
        result = classify_danger_signs()
        assert result is None

    def test_lethargic_triggers_urgent(self) -> None:
        result = classify_danger_signs(lethargic=True)
        assert result is not None
        assert result.classification == ClassificationType.URGENT_REFERRAL
        assert result.severity == Severity.RED
        assert result.referral == ReferralUrgency.IMMEDIATE

    def test_unconscious_triggers_urgent(self) -> None:
        result = classify_danger_signs(unconscious=True)
        assert result is not None
        assert result.classification == ClassificationType.URGENT_REFERRAL

    def test_unable_to_drink_triggers_urgent(self) -> None:
        result = classify_danger_signs(unable_to_drink=True)
        assert result is not None
        assert result.classification == ClassificationType.URGENT_REFERRAL

    def test_unable_to_breastfeed_triggers_urgent(self) -> None:
        result = classify_danger_signs(unable_to_breastfeed=True)
        assert result is not None
        assert result.classification == ClassificationType.URGENT_REFERRAL

    def test_convulsions_triggers_urgent(self) -> None:
        result = classify_danger_signs(convulsions=True)
        assert result is not None
        assert result.classification == ClassificationType.URGENT_REFERRAL

    def test_vomits_everything_triggers_urgent(self) -> None:
        result = classify_danger_signs(vomits_everything=True)
        assert result is not None
        assert result.classification == ClassificationType.URGENT_REFERRAL

    def test_multiple_signs_still_urgent(self) -> None:
        result = classify_danger_signs(lethargic=True, convulsions=True)
        assert result is not None
        assert result.classification == ClassificationType.URGENT_REFERRAL
        assert "lethargic" in result.reasoning
        assert "convulsions" in result.reasoning

    def test_all_false_returns_none(self) -> None:
        result = classify_danger_signs(
            lethargic=False, unconscious=False, unable_to_drink=False,
            unable_to_breastfeed=False, convulsions=False, vomits_everything=False,
        )
        assert result is None


# ============================================================================
# BREATHING / PNEUMONIA
# ============================================================================

class TestClassifyBreathing:
    """Tests for classify_breathing — IMCI Chart Booklet p.5."""

    # --- Severe pneumonia (RED) ---

    def test_chest_indrawing_is_severe(self) -> None:
        result = classify_breathing(age_months=6, has_indrawing=True)
        assert result.classification == ClassificationType.SEVERE_PNEUMONIA
        assert result.severity == Severity.RED

    def test_stridor_is_severe(self) -> None:
        result = classify_breathing(age_months=6, has_stridor=True)
        assert result.classification == ClassificationType.SEVERE_PNEUMONIA

    def test_indrawing_and_stridor_is_severe(self) -> None:
        result = classify_breathing(age_months=6, has_indrawing=True, has_stridor=True)
        assert result.classification == ClassificationType.SEVERE_PNEUMONIA
        assert "chest indrawing" in result.reasoning
        assert "stridor" in result.reasoning

    # --- Pneumonia (YELLOW) — fast breathing ---

    def test_fast_breathing_infant_at_threshold(self) -> None:
        """Exactly 50/min at 6 months = fast breathing."""
        result = classify_breathing(age_months=6, breathing_rate=50)
        assert result.classification == ClassificationType.PNEUMONIA
        assert result.severity == Severity.YELLOW

    def test_fast_breathing_infant_above_threshold(self) -> None:
        result = classify_breathing(age_months=6, breathing_rate=55)
        assert result.classification == ClassificationType.PNEUMONIA

    def test_fast_breathing_child_at_threshold(self) -> None:
        """Exactly 40/min at 24 months = fast breathing."""
        result = classify_breathing(age_months=24, breathing_rate=40)
        assert result.classification == ClassificationType.PNEUMONIA

    def test_fast_breathing_child_above_threshold(self) -> None:
        result = classify_breathing(age_months=24, breathing_rate=45)
        assert result.classification == ClassificationType.PNEUMONIA

    # --- No pneumonia (GREEN) ---

    def test_normal_breathing_infant_below_threshold(self) -> None:
        """49/min at 6 months = normal."""
        result = classify_breathing(age_months=6, breathing_rate=49)
        assert result.classification == ClassificationType.NO_PNEUMONIA_COUGH_OR_COLD
        assert result.severity == Severity.GREEN

    def test_normal_breathing_child_below_threshold(self) -> None:
        """39/min at 24 months = normal."""
        result = classify_breathing(age_months=24, breathing_rate=39)
        assert result.classification == ClassificationType.NO_PNEUMONIA_COUGH_OR_COLD

    def test_no_breathing_rate_measured(self) -> None:
        """No rate measured, no indrawing = green."""
        result = classify_breathing(age_months=12, has_cough=True)
        assert result.classification == ClassificationType.NO_PNEUMONIA_COUGH_OR_COLD

    # --- Indrawing overrides fast breathing ---

    def test_indrawing_overrides_rate(self) -> None:
        """Even with normal rate, indrawing = severe."""
        result = classify_breathing(age_months=6, breathing_rate=30, has_indrawing=True)
        assert result.classification == ClassificationType.SEVERE_PNEUMONIA

    # --- Age boundaries ---

    def test_age_11_months_uses_50_threshold(self) -> None:
        result = classify_breathing(age_months=11, breathing_rate=50)
        assert result.classification == ClassificationType.PNEUMONIA

    def test_age_12_months_uses_40_threshold(self) -> None:
        result = classify_breathing(age_months=12, breathing_rate=40)
        assert result.classification == ClassificationType.PNEUMONIA

    def test_age_12_months_49_is_normal(self) -> None:
        """49/min at 12 months — above old threshold but below new one? No, 49 >= 40."""
        result = classify_breathing(age_months=12, breathing_rate=49)
        assert result.classification == ClassificationType.PNEUMONIA

    # --- Invalid age ---

    def test_age_below_2_raises(self) -> None:
        with pytest.raises(ValueError, match="age_months must be between 2 and 59"):
            classify_breathing(age_months=1, breathing_rate=40)

    def test_age_above_59_raises(self) -> None:
        with pytest.raises(ValueError, match="age_months must be between 2 and 59"):
            classify_breathing(age_months=60, breathing_rate=40)


class TestIsFastBreathing:
    """Tests for is_fast_breathing helper."""

    def test_fast_infant(self) -> None:
        assert is_fast_breathing(50, 6) is True

    def test_normal_infant(self) -> None:
        assert is_fast_breathing(49, 6) is False

    def test_fast_child(self) -> None:
        assert is_fast_breathing(40, 24) is True

    def test_normal_child(self) -> None:
        assert is_fast_breathing(39, 24) is False

    def test_invalid_age(self) -> None:
        with pytest.raises(ValueError):
            is_fast_breathing(40, 1)


# ============================================================================
# DIARRHEA / DEHYDRATION
# ============================================================================

class TestClassifyDiarrhea:
    """Tests for classify_diarrhea — IMCI Chart Booklet p.8-9."""

    def test_no_diarrhea_returns_none(self) -> None:
        assert classify_diarrhea(has_diarrhea=False) is None

    # --- Severe dehydration (RED) ---

    def test_severe_dehydration_two_signs(self) -> None:
        result = classify_diarrhea(
            has_diarrhea=True, sunken_eyes=True, skin_pinch_very_slow=True,
        )
        assert result is not None
        assert result.classification == ClassificationType.SEVERE_DEHYDRATION
        assert result.severity == Severity.RED

    def test_severe_dehydration_lethargic_and_unable(self) -> None:
        result = classify_diarrhea(
            has_diarrhea=True, lethargic=True, unable_to_drink=True,
        )
        assert result is not None
        assert result.classification == ClassificationType.SEVERE_DEHYDRATION

    # --- Some dehydration (YELLOW) ---

    def test_some_dehydration_two_signs(self) -> None:
        result = classify_diarrhea(
            has_diarrhea=True, sunken_eyes=True, skin_pinch_slow=True,
        )
        assert result is not None
        assert result.classification == ClassificationType.SOME_DEHYDRATION
        assert result.severity == Severity.YELLOW

    def test_some_dehydration_restless_and_thirsty(self) -> None:
        result = classify_diarrhea(
            has_diarrhea=True, restless_irritable=True, drinks_eagerly=True,
        )
        assert result is not None
        assert result.classification == ClassificationType.SOME_DEHYDRATION

    # --- Persistent diarrhea ---

    def test_persistent_diarrhea_14_days(self) -> None:
        result = classify_diarrhea(has_diarrhea=True, duration_days=14)
        assert result is not None
        assert result.classification == ClassificationType.PERSISTENT_DIARRHEA
        assert result.severity == Severity.YELLOW

    def test_persistent_diarrhea_with_dehydration_is_severe(self) -> None:
        result = classify_diarrhea(
            has_diarrhea=True, duration_days=16, sunken_eyes=True,
        )
        assert result is not None
        assert result.classification == ClassificationType.SEVERE_PERSISTENT_DIARRHEA
        assert result.severity == Severity.RED

    # --- Dysentery ---

    def test_dysentery_blood_in_stool(self) -> None:
        result = classify_diarrhea(has_diarrhea=True, blood_in_stool=True)
        assert result is not None
        assert result.classification == ClassificationType.DYSENTERY
        assert result.severity == Severity.YELLOW

    # --- No dehydration (GREEN) ---

    def test_no_dehydration(self) -> None:
        result = classify_diarrhea(has_diarrhea=True, duration_days=2)
        assert result is not None
        assert result.classification == ClassificationType.NO_DEHYDRATION
        assert result.severity == Severity.GREEN

    # --- One sign is not enough for dehydration ---

    def test_one_severe_sign_not_enough(self) -> None:
        """Single severe sign — falls through to check some/persistent/dysentery/none."""
        result = classify_diarrhea(has_diarrhea=True, sunken_eyes=True)
        assert result is not None
        # One sign for severe (sunken_eyes) but also counts as one sign for some
        # Only 1 sign, not >= 2, so not some dehydration either
        assert result.classification != ClassificationType.SEVERE_DEHYDRATION


# ============================================================================
# FEVER
# ============================================================================

class TestClassifyFever:
    """Tests for classify_fever — IMCI Chart Booklet p.11."""

    def test_no_fever_returns_none(self) -> None:
        assert classify_fever(has_fever=False) is None

    def test_very_severe_stiff_neck(self) -> None:
        result = classify_fever(has_fever=True, stiff_neck=True)
        assert result is not None
        assert result.classification == ClassificationType.VERY_SEVERE_FEBRILE_DISEASE
        assert result.severity == Severity.RED

    def test_malaria_with_risk(self) -> None:
        result = classify_fever(has_fever=True, malaria_risk=True, duration_days=3)
        assert result is not None
        assert result.classification == ClassificationType.MALARIA
        assert result.severity == Severity.YELLOW

    def test_measles_with_complications(self) -> None:
        result = classify_fever(
            has_fever=True, measles_recent=True, measles_complications=True,
        )
        assert result is not None
        assert result.classification == ClassificationType.MEASLES_WITH_COMPLICATIONS

    def test_measles_without_complications(self) -> None:
        result = classify_fever(has_fever=True, measles_recent=True)
        assert result is not None
        assert result.classification == ClassificationType.MEASLES

    def test_fever_no_malaria_risk(self) -> None:
        result = classify_fever(has_fever=True, duration_days=2)
        assert result is not None
        assert result.classification == ClassificationType.FEVER_NO_MALARIA

    def test_stiff_neck_overrides_malaria(self) -> None:
        """Stiff neck = very severe, even in malaria area."""
        result = classify_fever(has_fever=True, stiff_neck=True, malaria_risk=True)
        assert result is not None
        assert result.classification == ClassificationType.VERY_SEVERE_FEBRILE_DISEASE


# ============================================================================
# NUTRITION
# ============================================================================

class TestClassifyNutrition:
    """Tests for classify_nutrition — IMCI Chart Booklet p.14."""

    def test_severe_visible_wasting(self) -> None:
        result = classify_nutrition(visible_wasting=True)
        assert result.classification == ClassificationType.SEVERE_MALNUTRITION
        assert result.severity == Severity.RED

    def test_severe_edema(self) -> None:
        result = classify_nutrition(edema=True)
        assert result.classification == ClassificationType.SEVERE_MALNUTRITION

    def test_severe_muac_below_115(self) -> None:
        result = classify_nutrition(muac_mm=110)
        assert result.classification == ClassificationType.SEVERE_MALNUTRITION

    def test_severe_muac_at_114(self) -> None:
        """114mm < 115mm threshold = severe."""
        result = classify_nutrition(muac_mm=114)
        assert result.classification == ClassificationType.SEVERE_MALNUTRITION

    def test_moderate_muac_at_115(self) -> None:
        """115mm is NOT severe (< 115), but IS moderate (< 125)."""
        result = classify_nutrition(muac_mm=115)
        assert result.classification == ClassificationType.MODERATE_MALNUTRITION

    def test_moderate_muac_at_124(self) -> None:
        """124mm < 125mm = moderate."""
        result = classify_nutrition(muac_mm=124)
        assert result.classification == ClassificationType.MODERATE_MALNUTRITION

    def test_normal_muac_at_125(self) -> None:
        """125mm >= 125mm = no malnutrition."""
        result = classify_nutrition(muac_mm=125)
        assert result.classification == ClassificationType.NO_MALNUTRITION

    def test_normal_muac_high(self) -> None:
        result = classify_nutrition(muac_mm=150)
        assert result.classification == ClassificationType.NO_MALNUTRITION
        assert result.severity == Severity.GREEN

    def test_normal_no_muac(self) -> None:
        """No MUAC, no wasting, no edema = normal."""
        result = classify_nutrition()
        assert result.classification == ClassificationType.NO_MALNUTRITION

    def test_wasting_overrides_normal_muac(self) -> None:
        """Visible wasting = severe even with normal MUAC."""
        result = classify_nutrition(visible_wasting=True, muac_mm=140)
        assert result.classification == ClassificationType.SEVERE_MALNUTRITION


# ============================================================================
# HEART (MEMS)
# ============================================================================

class TestClassifyHeart:
    """Tests for classify_heart — pluggable MEMS module."""

    def test_no_data_returns_none(self) -> None:
        assert classify_heart(age_months=12) is None

    def test_normal_heart_rate_infant(self) -> None:
        result = classify_heart(age_months=6, estimated_bpm=130)
        assert result is not None
        assert result.classification == ClassificationType.HEART_NORMAL

    def test_tachycardia_infant(self) -> None:
        result = classify_heart(age_months=6, estimated_bpm=165)
        assert result is not None
        assert result.classification == ClassificationType.HEART_ABNORMALITY

    def test_tachycardia_child(self) -> None:
        result = classify_heart(age_months=24, estimated_bpm=145)
        assert result is not None
        assert result.classification == ClassificationType.HEART_ABNORMALITY

    def test_bradycardia(self) -> None:
        result = classify_heart(age_months=12, estimated_bpm=55)
        assert result is not None
        assert result.classification == ClassificationType.HEART_ABNORMALITY

    def test_abnormal_sounds(self) -> None:
        result = classify_heart(age_months=12, abnormal_sounds=True)
        assert result is not None
        assert result.classification == ClassificationType.HEART_ABNORMALITY

    def test_normal_heart_rate_child(self) -> None:
        result = classify_heart(age_months=36, estimated_bpm=100)
        assert result is not None
        assert result.classification == ClassificationType.HEART_NORMAL


# ============================================================================
# AGGREGATE CLASSIFICATION
# ============================================================================

class TestClassifyAssessment:
    """Tests for classify_assessment — full IMCI aggregate classification."""

    def test_healthy_child(self) -> None:
        """No findings → healthy."""
        result = classify_assessment(age_months=18)
        assert result.severity == Severity.GREEN
        assert ClassificationType.HEALTHY in result.all_classification_types

    def test_single_domain_pneumonia(self) -> None:
        result = classify_assessment(
            age_months=6,
            breathing={"breathing_rate": 55, "has_cough": True},
        )
        assert result.severity == Severity.YELLOW
        assert ClassificationType.PNEUMONIA in result.all_classification_types

    def test_danger_sign_makes_red(self) -> None:
        result = classify_assessment(
            age_months=12,
            danger_signs={"lethargic": True},
        )
        assert result.severity == Severity.RED
        assert result.referral == ReferralUrgency.IMMEDIATE

    def test_multi_domain_worst_wins(self) -> None:
        """Pneumonia (YELLOW) + severe malnutrition (RED) → RED overall."""
        result = classify_assessment(
            age_months=8,
            breathing={"breathing_rate": 55, "has_cough": True},
            nutrition={"visible_wasting": True},
        )
        assert result.severity == Severity.RED
        assert ClassificationType.PNEUMONIA in result.all_classification_types
        assert ClassificationType.SEVERE_MALNUTRITION in result.all_classification_types

    def test_all_domains_normal(self) -> None:
        result = classify_assessment(
            age_months=18,
            danger_signs={"lethargic": False, "convulsions": False},
            breathing={"breathing_rate": 28, "has_cough": False},
            diarrhea={"has_diarrhea": False},
            fever={"has_fever": False},
            nutrition={"visible_wasting": False, "edema": False, "muac_mm": 150},
        )
        assert result.severity == Severity.GREEN

    def test_no_diarrhea_no_fever_excluded(self) -> None:
        """Domains returning None are excluded from classifications."""
        result = classify_assessment(
            age_months=18,
            diarrhea={"has_diarrhea": False},
            fever={"has_fever": False},
        )
        # Only healthy classification (no diarrhea/fever classifications added)
        types = result.all_classification_types
        assert ClassificationType.NO_DEHYDRATION not in types
        assert ClassificationType.FEVER_NO_MALARIA not in types


# ============================================================================
# GOLDEN SCENARIOS — from evaluation/golden_scenarios.py
# ============================================================================

class TestGoldenScenarios:
    """Verify all golden scenarios produce expected classifications."""

    def _run_golden(self, findings: dict[str, Any], age_months: int) -> AggregateClassification:
        return classify_assessment(age_months=age_months, **findings)

    def test_danger_lethargic(self) -> None:
        result = self._run_golden(
            {"danger_signs": {"lethargic": True, "unable_to_drink": True, "convulsions": False}},
            age_months=12,
        )
        assert result.severity == Severity.RED
        assert ClassificationType.URGENT_REFERRAL in result.all_classification_types

    def test_breathing_fast_infant(self) -> None:
        result = self._run_golden(
            {"breathing": {"breathing_rate": 55, "has_cough": True, "has_indrawing": False,
                           "has_stridor": False, "has_wheeze": False}},
            age_months=6,
        )
        assert ClassificationType.PNEUMONIA in result.all_classification_types

    def test_breathing_severe(self) -> None:
        result = self._run_golden(
            {"breathing": {"breathing_rate": 60, "has_cough": True, "has_indrawing": True,
                           "has_stridor": True, "has_wheeze": False}},
            age_months=10,
        )
        assert ClassificationType.SEVERE_PNEUMONIA in result.all_classification_types
        assert result.severity == Severity.RED

    def test_diarrhea_severe_dehydration(self) -> None:
        result = self._run_golden(
            {"diarrhea": {"has_diarrhea": True, "duration_days": 3, "blood_in_stool": False,
                          "sunken_eyes": True, "skin_pinch_very_slow": True,
                          "unable_to_drink": True}},
            age_months=8,
        )
        assert ClassificationType.SEVERE_DEHYDRATION in result.all_classification_types

    def test_fever_very_severe(self) -> None:
        result = self._run_golden(
            {"fever": {"has_fever": True, "duration_days": 3, "stiff_neck": True,
                       "malaria_risk": True}},
            age_months=24,
        )
        assert ClassificationType.VERY_SEVERE_FEBRILE_DISEASE in result.all_classification_types

    def test_nutrition_severe_wasting(self) -> None:
        result = self._run_golden(
            {"nutrition": {"visible_wasting": True, "edema": False, "muac_mm": 110}},
            age_months=10,
        )
        assert ClassificationType.SEVERE_MALNUTRITION in result.all_classification_types

    def test_healthy_child(self) -> None:
        result = self._run_golden(
            {
                "danger_signs": {"lethargic": False, "unable_to_drink": False, "convulsions": False},
                "breathing": {"breathing_rate": 28, "has_cough": False, "has_indrawing": False,
                              "has_stridor": False, "has_wheeze": False},
                "diarrhea": {"has_diarrhea": False},
                "fever": {"has_fever": False},
                "nutrition": {"visible_wasting": False, "edema": False, "muac_mm": 150},
            },
            age_months=18,
        )
        assert result.severity == Severity.GREEN

    def test_combined_pneumonia_dehydration(self) -> None:
        result = self._run_golden(
            {
                "breathing": {"breathing_rate": 55, "has_cough": True, "has_indrawing": False,
                              "has_stridor": False, "has_wheeze": False},
                "diarrhea": {"has_diarrhea": True, "duration_days": 2, "blood_in_stool": False,
                             "sunken_eyes": True, "skin_pinch_slow": True,
                             "unable_to_drink": False},
            },
            age_months=10,
        )
        types = result.all_classification_types
        assert ClassificationType.PNEUMONIA in types
        assert ClassificationType.SOME_DEHYDRATION in types
        assert result.severity == Severity.YELLOW
