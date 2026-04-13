"""Golden Scenarios — 20+ WHO IMCI test cases with known-correct classifications.

Each scenario is derived from the WHO IMCI Chart Booklet and has a
deterministic expected classification. These are ground truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from malaika.types import ClassificationType, ReferralUrgency, Severity


@dataclass(frozen=True)
class GoldenScenario:
    """A single evaluation scenario with known-correct WHO IMCI classification.

    Attributes:
        name: Unique snake_case identifier.
        description: Human-readable scenario description.
        who_source: WHO IMCI Chart Booklet citation.
        age_months: Child's age in months (2-59).
        findings: Structured clinical findings per IMCI domain.
        expected_classifications: List of expected ClassificationType values.
        expected_severity: Expected Severity (RED/YELLOW/GREEN).
        expected_referral: Expected ReferralUrgency.
        level: Test level — "protocol" (no GPU), "perception" (mock), "e2e" (GPU).
    """

    name: str
    description: str
    who_source: str
    age_months: int
    findings: dict[str, Any]
    expected_classifications: list[ClassificationType]
    expected_severity: Severity
    expected_referral: ReferralUrgency
    level: str = "protocol"


# ---------------------------------------------------------------------------
# Golden Scenarios — WHO IMCI Chart Booklet
# ---------------------------------------------------------------------------

GOLDEN_SCENARIOS: list[GoldenScenario] = [
    # === DANGER SIGNS ===
    GoldenScenario(
        name="danger_lethargic",
        description="Lethargic child, unable to drink — immediate danger sign",
        who_source="IMCI Chart Booklet, p.2: General danger signs",
        age_months=12,
        findings={
            "danger_signs": {"lethargic": True, "unable_to_drink": True, "convulsions": False},
        },
        expected_classifications=[ClassificationType.URGENT_REFERRAL],
        expected_severity=Severity.RED,
        expected_referral=ReferralUrgency.IMMEDIATE,
    ),
    GoldenScenario(
        name="danger_convulsions",
        description="Child with reported convulsions",
        who_source="IMCI Chart Booklet, p.2: General danger signs",
        age_months=24,
        findings={
            "danger_signs": {"lethargic": False, "unable_to_drink": False, "convulsions": True},
        },
        expected_classifications=[ClassificationType.URGENT_REFERRAL],
        expected_severity=Severity.RED,
        expected_referral=ReferralUrgency.IMMEDIATE,
    ),
    GoldenScenario(
        name="danger_vomiting_everything",
        description="Child vomits everything — cannot keep fluids down",
        who_source="IMCI Chart Booklet, p.2: General danger signs",
        age_months=18,
        findings={
            "danger_signs": {"lethargic": False, "unable_to_drink": False,
                             "convulsions": False, "vomits_everything": True},
        },
        expected_classifications=[ClassificationType.URGENT_REFERRAL],
        expected_severity=Severity.RED,
        expected_referral=ReferralUrgency.IMMEDIATE,
    ),

    # === BREATHING / PNEUMONIA ===
    GoldenScenario(
        name="breathing_fast_infant",
        description="55 breaths/min in 6-month-old with cough — fast breathing",
        who_source="IMCI Chart Booklet, p.5: 50+ breaths/min for 2-11 months",
        age_months=6,
        findings={
            "breathing": {"breathing_rate": 55, "has_cough": True, "has_indrawing": False,
                          "has_stridor": False, "has_wheeze": False},
        },
        expected_classifications=[ClassificationType.PNEUMONIA],
        expected_severity=Severity.YELLOW,
        expected_referral=ReferralUrgency.WITHIN_24H,
    ),
    GoldenScenario(
        name="breathing_fast_child",
        description="45 breaths/min in 24-month-old — fast breathing",
        who_source="IMCI Chart Booklet, p.5: 40+ breaths/min for 12-59 months",
        age_months=24,
        findings={
            "breathing": {"breathing_rate": 45, "has_cough": True, "has_indrawing": False,
                          "has_stridor": False, "has_wheeze": False},
        },
        expected_classifications=[ClassificationType.PNEUMONIA],
        expected_severity=Severity.YELLOW,
        expected_referral=ReferralUrgency.WITHIN_24H,
    ),
    GoldenScenario(
        name="breathing_severe_pneumonia",
        description="Chest indrawing + stridor at rest — severe pneumonia",
        who_source="IMCI Chart Booklet, p.5: Chest indrawing = severe pneumonia",
        age_months=10,
        findings={
            "breathing": {"breathing_rate": 60, "has_cough": True, "has_indrawing": True,
                          "has_stridor": True, "has_wheeze": False},
        },
        expected_classifications=[ClassificationType.SEVERE_PNEUMONIA],
        expected_severity=Severity.RED,
        expected_referral=ReferralUrgency.IMMEDIATE,
    ),
    GoldenScenario(
        name="breathing_normal_cough",
        description="Normal breathing rate, cough — no pneumonia",
        who_source="IMCI Chart Booklet, p.5: No fast breathing, no indrawing",
        age_months=36,
        findings={
            "breathing": {"breathing_rate": 30, "has_cough": True, "has_indrawing": False,
                          "has_stridor": False, "has_wheeze": False},
        },
        expected_classifications=[ClassificationType.NO_PNEUMONIA_COUGH_OR_COLD],
        expected_severity=Severity.GREEN,
        expected_referral=ReferralUrgency.NONE,
    ),

    # === DIARRHEA ===
    GoldenScenario(
        name="diarrhea_severe_dehydration",
        description="Lethargic, sunken eyes, very slow skin pinch — severe dehydration",
        who_source="IMCI Chart Booklet, p.8: 2+ signs of severe dehydration",
        age_months=8,
        findings={
            "diarrhea": {"has_diarrhea": True, "duration_days": 3, "blood_in_stool": False,
                         "sunken_eyes": True, "skin_pinch_very_slow": True,
                         "unable_to_drink": True},
        },
        expected_classifications=[ClassificationType.SEVERE_DEHYDRATION],
        expected_severity=Severity.RED,
        expected_referral=ReferralUrgency.IMMEDIATE,
    ),
    GoldenScenario(
        name="diarrhea_some_dehydration",
        description="Restless, sunken eyes, slow skin pinch — some dehydration",
        who_source="IMCI Chart Booklet, p.8: 2+ signs of some dehydration",
        age_months=14,
        findings={
            "diarrhea": {"has_diarrhea": True, "duration_days": 2, "blood_in_stool": False,
                         "sunken_eyes": True, "skin_pinch_slow": True,
                         "unable_to_drink": False},
        },
        expected_classifications=[ClassificationType.SOME_DEHYDRATION],
        expected_severity=Severity.YELLOW,
        expected_referral=ReferralUrgency.WITHIN_24H,
    ),
    GoldenScenario(
        name="diarrhea_no_dehydration",
        description="Diarrhea 2 days, no dehydration signs",
        who_source="IMCI Chart Booklet, p.8: No dehydration signs",
        age_months=20,
        findings={
            "diarrhea": {"has_diarrhea": True, "duration_days": 2, "blood_in_stool": False,
                         "sunken_eyes": False, "skin_pinch_slow": False,
                         "unable_to_drink": False},
        },
        expected_classifications=[ClassificationType.NO_DEHYDRATION],
        expected_severity=Severity.GREEN,
        expected_referral=ReferralUrgency.NONE,
    ),
    GoldenScenario(
        name="diarrhea_dysentery",
        description="Blood in stool — dysentery",
        who_source="IMCI Chart Booklet, p.9: Blood in stool = dysentery",
        age_months=30,
        findings={
            "diarrhea": {"has_diarrhea": True, "duration_days": 4, "blood_in_stool": True,
                         "sunken_eyes": False, "skin_pinch_slow": False,
                         "unable_to_drink": False},
        },
        expected_classifications=[ClassificationType.DYSENTERY],
        expected_severity=Severity.YELLOW,
        expected_referral=ReferralUrgency.WITHIN_24H,
    ),
    GoldenScenario(
        name="diarrhea_persistent",
        description="Diarrhea for 14+ days — persistent diarrhea",
        who_source="IMCI Chart Booklet, p.9: Diarrhea >= 14 days",
        age_months=16,
        findings={
            "diarrhea": {"has_diarrhea": True, "duration_days": 16, "blood_in_stool": False,
                         "sunken_eyes": False, "skin_pinch_slow": False,
                         "unable_to_drink": False},
        },
        expected_classifications=[ClassificationType.PERSISTENT_DIARRHEA],
        expected_severity=Severity.YELLOW,
        expected_referral=ReferralUrgency.WITHIN_24H,
    ),

    # === FEVER ===
    GoldenScenario(
        name="fever_very_severe",
        description="Fever with stiff neck — very severe febrile disease",
        who_source="IMCI Chart Booklet, p.11: Stiff neck = very severe febrile disease",
        age_months=24,
        findings={
            "fever": {"has_fever": True, "duration_days": 3, "stiff_neck": True,
                      "malaria_risk": True},
        },
        expected_classifications=[ClassificationType.VERY_SEVERE_FEBRILE_DISEASE],
        expected_severity=Severity.RED,
        expected_referral=ReferralUrgency.IMMEDIATE,
    ),
    GoldenScenario(
        name="fever_malaria",
        description="Fever 3 days in malaria-endemic area",
        who_source="IMCI Chart Booklet, p.11: Fever + malaria risk",
        age_months=36,
        findings={
            "fever": {"has_fever": True, "duration_days": 3, "stiff_neck": False,
                      "malaria_risk": True},
        },
        expected_classifications=[ClassificationType.MALARIA],
        expected_severity=Severity.YELLOW,
        expected_referral=ReferralUrgency.WITHIN_24H,
    ),
    GoldenScenario(
        name="fever_no_malaria",
        description="Fever 2 days, no malaria risk area, no danger signs",
        who_source="IMCI Chart Booklet, p.11: Fever without malaria risk",
        age_months=48,
        findings={
            "fever": {"has_fever": True, "duration_days": 2, "stiff_neck": False,
                      "malaria_risk": False},
        },
        expected_classifications=[ClassificationType.FEVER_NO_MALARIA],
        expected_severity=Severity.YELLOW,
        expected_referral=ReferralUrgency.WITHIN_24H,
    ),

    # === NUTRITION ===
    GoldenScenario(
        name="nutrition_severe_wasting",
        description="Visible severe wasting — severe malnutrition",
        who_source="IMCI Chart Booklet, p.14: Visible severe wasting",
        age_months=10,
        findings={
            "nutrition": {"visible_wasting": True, "edema": False, "muac_mm": 110},
        },
        expected_classifications=[ClassificationType.SEVERE_MALNUTRITION],
        expected_severity=Severity.RED,
        expected_referral=ReferralUrgency.IMMEDIATE,
    ),
    GoldenScenario(
        name="nutrition_edema",
        description="Edema both feet — severe malnutrition",
        who_source="IMCI Chart Booklet, p.14: Edema both feet",
        age_months=24,
        findings={
            "nutrition": {"visible_wasting": False, "edema": True, "muac_mm": 130},
        },
        expected_classifications=[ClassificationType.SEVERE_MALNUTRITION],
        expected_severity=Severity.RED,
        expected_referral=ReferralUrgency.IMMEDIATE,
    ),
    GoldenScenario(
        name="nutrition_normal",
        description="Normal nutrition, MUAC 145mm",
        who_source="IMCI Chart Booklet, p.14: No wasting, no edema, MUAC >= 125mm",
        age_months=30,
        findings={
            "nutrition": {"visible_wasting": False, "edema": False, "muac_mm": 145},
        },
        expected_classifications=[ClassificationType.NO_MALNUTRITION],
        expected_severity=Severity.GREEN,
        expected_referral=ReferralUrgency.NONE,
    ),

    # === HEALTHY CHILD ===
    GoldenScenario(
        name="healthy_child",
        description="No danger signs, normal breathing, no diarrhea, no fever, normal nutrition",
        who_source="IMCI Chart Booklet: No classifications triggered",
        age_months=18,
        findings={
            "danger_signs": {"lethargic": False, "unable_to_drink": False, "convulsions": False},
            "breathing": {"breathing_rate": 28, "has_cough": False, "has_indrawing": False,
                          "has_stridor": False, "has_wheeze": False},
            "diarrhea": {"has_diarrhea": False},
            "fever": {"has_fever": False},
            "nutrition": {"visible_wasting": False, "edema": False, "muac_mm": 150},
        },
        expected_classifications=[ClassificationType.HEALTHY],
        expected_severity=Severity.GREEN,
        expected_referral=ReferralUrgency.NONE,
    ),

    # === COMBINED (multi-domain) ===
    GoldenScenario(
        name="combined_pneumonia_dehydration",
        description="Fast breathing + some dehydration — both classified",
        who_source="IMCI Chart Booklet: Independent classification per domain",
        age_months=10,
        findings={
            "breathing": {"breathing_rate": 55, "has_cough": True, "has_indrawing": False,
                          "has_stridor": False, "has_wheeze": False},
            "diarrhea": {"has_diarrhea": True, "duration_days": 2, "blood_in_stool": False,
                         "sunken_eyes": True, "skin_pinch_slow": True,
                         "unable_to_drink": False},
        },
        expected_classifications=[
            ClassificationType.PNEUMONIA,
            ClassificationType.SOME_DEHYDRATION,
        ],
        expected_severity=Severity.YELLOW,
        expected_referral=ReferralUrgency.WITHIN_24H,
    ),
    GoldenScenario(
        name="combined_severe_pneumonia_malnutrition",
        description="Chest indrawing + severe wasting — multiple red flags",
        who_source="IMCI Chart Booklet: Worst severity wins",
        age_months=8,
        findings={
            "breathing": {"breathing_rate": 62, "has_cough": True, "has_indrawing": True,
                          "has_stridor": False, "has_wheeze": False},
            "nutrition": {"visible_wasting": True, "edema": False, "muac_mm": 108},
        },
        expected_classifications=[
            ClassificationType.SEVERE_PNEUMONIA,
            ClassificationType.SEVERE_MALNUTRITION,
        ],
        expected_severity=Severity.RED,
        expected_referral=ReferralUrgency.IMMEDIATE,
    ),
]
