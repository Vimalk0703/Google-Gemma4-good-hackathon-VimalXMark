"""WHO IMCI Protocol — deterministic classification logic.

THIS IS THE MEDICAL SAFETY BOUNDARY.

Every function in this module is pure: same input → same output, always.
Every threshold is from the WHO IMCI Chart Booklet with page citations.
This module MUST NOT import inference.py or call any AI.

Reference: WHO IMCI Chart Booklet (2014 revision, reaffirmed 2023)
https://www.who.int/publications/i/item/9789241506823
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from malaika.types import (
    ClassificationType,
    ReferralUrgency,
    Severity,
)


# ============================================================================
# WHO THRESHOLDS — Constants
# ============================================================================

# Breathing rate thresholds (breaths per minute)
# Source: IMCI Chart Booklet, p.5
FAST_BREATHING_THRESHOLD_2_TO_11_MONTHS: int = 50   # >= 50 = fast breathing
FAST_BREATHING_THRESHOLD_12_TO_59_MONTHS: int = 40   # >= 40 = fast breathing

# Diarrhea duration thresholds (days)
# Source: IMCI Chart Booklet, p.9
PERSISTENT_DIARRHEA_THRESHOLD_DAYS: int = 14  # >= 14 days = persistent

# Fever duration thresholds (days)
# Source: IMCI Chart Booklet, p.11
FEVER_DURATION_CONCERN_DAYS: int = 7  # >= 7 days = prolonged fever

# MUAC thresholds (mm)
# Source: IMCI Chart Booklet, p.14
MUAC_SEVERE_THRESHOLD_MM: int = 115   # < 115mm = severe acute malnutrition
MUAC_MODERATE_THRESHOLD_MM: int = 125  # 115-124mm = moderate acute malnutrition

# Dehydration classification requires this many signs
# Source: IMCI Chart Booklet, p.8
SEVERE_DEHYDRATION_MIN_SIGNS: int = 2
SOME_DEHYDRATION_MIN_SIGNS: int = 2

# Heart rate thresholds (BPM) — pediatric
# Source: Pediatric Advanced Life Support (PALS) guidelines
HEART_RATE_TACHYCARDIA_INFANT: int = 160   # > 160 in <1yr
HEART_RATE_TACHYCARDIA_CHILD: int = 140    # > 140 in 1-5yr
HEART_RATE_BRADYCARDIA: int = 60           # < 60 at any age


# ============================================================================
# Classification Result
# ============================================================================

@dataclass(frozen=True)
class DomainClassification:
    """Result of classifying one IMCI domain.

    Attributes:
        classification: The WHO classification assigned.
        severity: RED/YELLOW/GREEN severity level.
        referral: How urgently the child needs a facility.
        reasoning: Brief explanation of why this classification was assigned.
    """

    classification: ClassificationType
    severity: Severity
    referral: ReferralUrgency
    reasoning: str


@dataclass
class AggregateClassification:
    """Final classification combining all IMCI domains.

    The worst severity across all domains determines the final severity.
    All individual classifications are preserved.
    """

    classifications: list[DomainClassification] = field(default_factory=list)

    @property
    def severity(self) -> Severity:
        """Worst severity across all domains. RED > YELLOW > GREEN."""
        if not self.classifications:
            return Severity.GREEN
        severity_order = {Severity.RED: 2, Severity.YELLOW: 1, Severity.GREEN: 0}
        worst = max(self.classifications, key=lambda c: severity_order[c.severity])
        return worst.severity

    @property
    def referral(self) -> ReferralUrgency:
        """Most urgent referral across all domains."""
        if not self.classifications:
            return ReferralUrgency.NONE
        urgency_order = {
            ReferralUrgency.IMMEDIATE: 2,
            ReferralUrgency.WITHIN_24H: 1,
            ReferralUrgency.NONE: 0,
        }
        worst = max(self.classifications, key=lambda c: urgency_order[c.referral])
        return worst.referral

    @property
    def all_classification_types(self) -> list[ClassificationType]:
        """All classification types assigned across domains."""
        return [c.classification for c in self.classifications]


# ============================================================================
# DANGER SIGNS — IMCI Chart Booklet p.2
# ============================================================================

def classify_danger_signs(
    *,
    lethargic: bool = False,
    unconscious: bool = False,
    unable_to_drink: bool = False,
    unable_to_breastfeed: bool = False,
    convulsions: bool = False,
    vomits_everything: bool = False,
) -> DomainClassification | None:
    """Classify general danger signs per WHO IMCI.

    ANY single danger sign present → URGENT REFERRAL (RED).
    No danger signs → returns None (no classification for this domain).

    Source: IMCI Chart Booklet, p.2 — "Check for general danger signs"

    Args:
        lethargic: Child is abnormally sleepy and difficult to wake.
        unconscious: Child cannot be woken.
        unable_to_drink: Child cannot drink or breastfeed.
        unable_to_breastfeed: Infant cannot attach to breast.
        convulsions: Child has had convulsions during this illness.
        vomits_everything: Child vomits immediately after eating/drinking.

    Returns:
        DomainClassification with URGENT_REFERRAL if any sign present, None otherwise.
    """
    signs_present = []
    if lethargic:
        signs_present.append("lethargic")
    if unconscious:
        signs_present.append("unconscious")
    if unable_to_drink:
        signs_present.append("unable to drink")
    if unable_to_breastfeed:
        signs_present.append("unable to breastfeed")
    if convulsions:
        signs_present.append("convulsions")
    if vomits_everything:
        signs_present.append("vomits everything")

    if not signs_present:
        return None

    return DomainClassification(
        classification=ClassificationType.URGENT_REFERRAL,
        severity=Severity.RED,
        referral=ReferralUrgency.IMMEDIATE,
        reasoning=f"General danger sign(s): {', '.join(signs_present)}. "
                  f"WHO IMCI p.2: Any danger sign → urgent referral.",
    )


# ============================================================================
# BREATHING / PNEUMONIA — IMCI Chart Booklet p.5
# ============================================================================

def classify_breathing(
    *,
    age_months: int,
    has_cough: bool = False,
    breathing_rate: int | None = None,
    has_indrawing: bool = False,
    has_stridor: bool = False,
    has_wheeze: bool = False,
) -> DomainClassification:
    """Classify cough/breathing per WHO IMCI.

    Classification hierarchy (worst first):
    1. Chest indrawing OR stridor at rest → SEVERE PNEUMONIA (RED)
    2. Fast breathing for age → PNEUMONIA (YELLOW)
    3. Cough but no fast breathing → NO PNEUMONIA: COUGH OR COLD (GREEN)

    Source: IMCI Chart Booklet, p.5 — "Does the child have cough or difficult breathing?"

    Args:
        age_months: Child's age in months (must be 2-59).
        has_cough: Whether the child has a cough.
        breathing_rate: Breaths per minute (None if not measured).
        has_indrawing: Subcostal/intercostal chest indrawing observed.
        has_stridor: Stridor heard when child is calm.
        has_wheeze: Wheezing heard.

    Returns:
        DomainClassification for breathing/pneumonia.

    Raises:
        ValueError: If age_months is outside 2-59 range.
    """
    if not (2 <= age_months <= 59):
        raise ValueError(
            f"age_months must be between 2 and 59 for IMCI, got {age_months}"
        )

    # SEVERE PNEUMONIA: chest indrawing or stridor at rest
    # Source: IMCI Chart Booklet p.5, pink row
    if has_indrawing or has_stridor:
        signs = []
        if has_indrawing:
            signs.append("chest indrawing")
        if has_stridor:
            signs.append("stridor at rest")
        return DomainClassification(
            classification=ClassificationType.SEVERE_PNEUMONIA,
            severity=Severity.RED,
            referral=ReferralUrgency.IMMEDIATE,
            reasoning=f"Severe pneumonia: {', '.join(signs)}. WHO IMCI p.5.",
        )

    # PNEUMONIA: fast breathing for age
    # Source: IMCI Chart Booklet p.5, yellow row
    if breathing_rate is not None:
        threshold = _get_breathing_threshold(age_months)
        if breathing_rate >= threshold:
            return DomainClassification(
                classification=ClassificationType.PNEUMONIA,
                severity=Severity.YELLOW,
                referral=ReferralUrgency.WITHIN_24H,
                reasoning=f"Pneumonia: breathing rate {breathing_rate}/min "
                          f"≥ threshold {threshold}/min for age {age_months}mo. WHO IMCI p.5.",
            )

    # NO PNEUMONIA: cough or cold
    # Source: IMCI Chart Booklet p.5, green row
    return DomainClassification(
        classification=ClassificationType.NO_PNEUMONIA_COUGH_OR_COLD,
        severity=Severity.GREEN,
        referral=ReferralUrgency.NONE,
        reasoning=f"No pneumonia: {'cough present, ' if has_cough else ''}"
                  f"no fast breathing, no indrawing. WHO IMCI p.5.",
    )


def _get_breathing_threshold(age_months: int) -> int:
    """Get fast breathing threshold for age group.

    Source: IMCI Chart Booklet p.5
    - 2 to 11 months: ≥ 50 breaths/min
    - 12 to 59 months: ≥ 40 breaths/min
    """
    if 2 <= age_months <= 11:
        return FAST_BREATHING_THRESHOLD_2_TO_11_MONTHS
    return FAST_BREATHING_THRESHOLD_12_TO_59_MONTHS


def is_fast_breathing(rate: int, age_months: int) -> bool:
    """Check if breathing rate exceeds WHO IMCI threshold for age group.

    Args:
        rate: Breaths per minute.
        age_months: Child's age in months (2-59).

    Returns:
        True if rate >= threshold for age group.

    Raises:
        ValueError: If age outside 2-59 range.
    """
    if not (2 <= age_months <= 59):
        raise ValueError(f"age_months must be between 2 and 59, got {age_months}")
    return rate >= _get_breathing_threshold(age_months)


# ============================================================================
# DIARRHEA / DEHYDRATION — IMCI Chart Booklet p.8-9
# ============================================================================

def classify_diarrhea(
    *,
    has_diarrhea: bool,
    duration_days: int = 0,
    blood_in_stool: bool = False,
    sunken_eyes: bool = False,
    skin_pinch_slow: bool = False,
    skin_pinch_very_slow: bool = False,
    unable_to_drink: bool = False,
    drinks_eagerly: bool = False,
    restless_irritable: bool = False,
    lethargic: bool = False,
) -> DomainClassification | None:
    """Classify diarrhea and dehydration per WHO IMCI.

    Returns None if no diarrhea. Otherwise classifies dehydration level,
    persistent diarrhea, or dysentery.

    Multiple classifications can apply (e.g., some dehydration + dysentery),
    but this function returns the WORST single classification.

    Source: IMCI Chart Booklet, p.8-9

    Args:
        has_diarrhea: Whether the child has diarrhea.
        duration_days: How many days diarrhea has lasted.
        blood_in_stool: Whether blood was seen in stool.
        sunken_eyes: Eyes appear sunken.
        skin_pinch_slow: Skin pinch goes back slowly (1-2 seconds).
        skin_pinch_very_slow: Skin pinch goes back very slowly (>2 seconds).
        unable_to_drink: Child cannot drink at all.
        drinks_eagerly: Child drinks eagerly/thirstily.
        restless_irritable: Child is restless and irritable.
        lethargic: Child is lethargic or unconscious.

    Returns:
        DomainClassification or None if no diarrhea.
    """
    if not has_diarrhea:
        return None

    # Count severe dehydration signs
    # Source: IMCI Chart Booklet p.8, pink row
    severe_signs = sum([
        lethargic,              # Lethargic or unconscious
        sunken_eyes,            # Sunken eyes
        unable_to_drink,        # Unable to drink or drinks poorly
        skin_pinch_very_slow,   # Skin pinch goes back very slowly
    ])

    if severe_signs >= SEVERE_DEHYDRATION_MIN_SIGNS:
        return DomainClassification(
            classification=ClassificationType.SEVERE_DEHYDRATION,
            severity=Severity.RED,
            referral=ReferralUrgency.IMMEDIATE,
            reasoning=f"Severe dehydration: {severe_signs} signs present "
                      f"(≥{SEVERE_DEHYDRATION_MIN_SIGNS} required). WHO IMCI p.8.",
        )

    # Count some dehydration signs
    # Source: IMCI Chart Booklet p.8, yellow row
    some_signs = sum([
        restless_irritable,     # Restless, irritable
        sunken_eyes,            # Sunken eyes
        drinks_eagerly,         # Drinks eagerly, thirsty
        skin_pinch_slow,        # Skin pinch goes back slowly
    ])

    if some_signs >= SOME_DEHYDRATION_MIN_SIGNS:
        return DomainClassification(
            classification=ClassificationType.SOME_DEHYDRATION,
            severity=Severity.YELLOW,
            referral=ReferralUrgency.WITHIN_24H,
            reasoning=f"Some dehydration: {some_signs} signs present "
                      f"(≥{SOME_DEHYDRATION_MIN_SIGNS} required). WHO IMCI p.8.",
        )

    # Persistent diarrhea (≥14 days)
    # Source: IMCI Chart Booklet p.9
    if duration_days >= PERSISTENT_DIARRHEA_THRESHOLD_DAYS:
        # Check if severe (with dehydration) or non-severe
        if severe_signs > 0 or some_signs > 0:
            return DomainClassification(
                classification=ClassificationType.SEVERE_PERSISTENT_DIARRHEA,
                severity=Severity.RED,
                referral=ReferralUrgency.IMMEDIATE,
                reasoning=f"Severe persistent diarrhea: {duration_days} days "
                          f"with dehydration signs. WHO IMCI p.9.",
            )
        return DomainClassification(
            classification=ClassificationType.PERSISTENT_DIARRHEA,
            severity=Severity.YELLOW,
            referral=ReferralUrgency.WITHIN_24H,
            reasoning=f"Persistent diarrhea: {duration_days} days "
                      f"(≥{PERSISTENT_DIARRHEA_THRESHOLD_DAYS}). WHO IMCI p.9.",
        )

    # Dysentery (blood in stool)
    # Source: IMCI Chart Booklet p.9
    if blood_in_stool:
        return DomainClassification(
            classification=ClassificationType.DYSENTERY,
            severity=Severity.YELLOW,
            referral=ReferralUrgency.WITHIN_24H,
            reasoning="Dysentery: blood in stool. WHO IMCI p.9.",
        )

    # No dehydration
    # Source: IMCI Chart Booklet p.8, green row
    return DomainClassification(
        classification=ClassificationType.NO_DEHYDRATION,
        severity=Severity.GREEN,
        referral=ReferralUrgency.NONE,
        reasoning="No dehydration: insufficient dehydration signs. WHO IMCI p.8.",
    )


# ============================================================================
# FEVER — IMCI Chart Booklet p.11
# ============================================================================

def classify_fever(
    *,
    has_fever: bool,
    duration_days: int = 0,
    stiff_neck: bool = False,
    malaria_risk: bool = False,
    measles_recent: bool = False,
    measles_complications: bool = False,
) -> DomainClassification | None:
    """Classify fever per WHO IMCI.

    Source: IMCI Chart Booklet, p.11 — "Does the child have fever?"

    Args:
        has_fever: Whether the child has fever (reported or measured ≥37.5°C).
        duration_days: Duration of fever in days.
        stiff_neck: Child has a stiff neck.
        malaria_risk: Whether the area has malaria transmission.
        measles_recent: Child had measles within last 3 months.
        measles_complications: Complications present (mouth ulcers, eye infection, etc.).

    Returns:
        DomainClassification or None if no fever.
    """
    if not has_fever:
        return None

    # VERY SEVERE FEBRILE DISEASE
    # Source: IMCI Chart Booklet p.11, pink row
    # Stiff neck = meningitis risk → immediate referral
    if stiff_neck:
        return DomainClassification(
            classification=ClassificationType.VERY_SEVERE_FEBRILE_DISEASE,
            severity=Severity.RED,
            referral=ReferralUrgency.IMMEDIATE,
            reasoning="Very severe febrile disease: stiff neck present. WHO IMCI p.11.",
        )

    # MALARIA (in malaria-risk area)
    # Source: IMCI Chart Booklet p.11, yellow row
    if malaria_risk:
        return DomainClassification(
            classification=ClassificationType.MALARIA,
            severity=Severity.YELLOW,
            referral=ReferralUrgency.WITHIN_24H,
            reasoning=f"Malaria: fever {duration_days} days in malaria-risk area. "
                      f"WHO IMCI p.11.",
        )

    # MEASLES WITH COMPLICATIONS
    # Source: IMCI Chart Booklet p.12
    if measles_recent and measles_complications:
        return DomainClassification(
            classification=ClassificationType.MEASLES_WITH_COMPLICATIONS,
            severity=Severity.YELLOW,
            referral=ReferralUrgency.WITHIN_24H,
            reasoning="Measles with complications. WHO IMCI p.12.",
        )

    # MEASLES (without complications)
    if measles_recent:
        return DomainClassification(
            classification=ClassificationType.MEASLES,
            severity=Severity.YELLOW,
            referral=ReferralUrgency.WITHIN_24H,
            reasoning="Measles (recent, without complications). WHO IMCI p.12.",
        )

    # FEVER — no specific cause identified
    # Source: IMCI Chart Booklet p.11, yellow/green row
    return DomainClassification(
        classification=ClassificationType.FEVER_NO_MALARIA,
        severity=Severity.YELLOW,
        referral=ReferralUrgency.WITHIN_24H,
        reasoning=f"Fever {duration_days} days, no malaria risk, "
                  f"no stiff neck. WHO IMCI p.11.",
    )


# ============================================================================
# NUTRITION — IMCI Chart Booklet p.14
# ============================================================================

def classify_nutrition(
    *,
    visible_wasting: bool = False,
    edema: bool = False,
    muac_mm: int | None = None,
) -> DomainClassification:
    """Classify nutritional status per WHO IMCI.

    Source: IMCI Chart Booklet, p.14 — "Check for malnutrition"

    Args:
        visible_wasting: Severe visible wasting observed.
        edema: Edema of both feet.
        muac_mm: Mid-upper arm circumference in mm (if measured).

    Returns:
        DomainClassification for nutrition.
    """
    # SEVERE MALNUTRITION
    # Source: IMCI Chart Booklet p.14, pink row
    # Visible severe wasting OR edema both feet OR MUAC < 115mm
    is_severe = (
        visible_wasting
        or edema
        or (muac_mm is not None and muac_mm < MUAC_SEVERE_THRESHOLD_MM)
    )

    if is_severe:
        reasons = []
        if visible_wasting:
            reasons.append("visible severe wasting")
        if edema:
            reasons.append("edema both feet")
        if muac_mm is not None and muac_mm < MUAC_SEVERE_THRESHOLD_MM:
            reasons.append(f"MUAC {muac_mm}mm < {MUAC_SEVERE_THRESHOLD_MM}mm")

        return DomainClassification(
            classification=ClassificationType.SEVERE_MALNUTRITION,
            severity=Severity.RED,
            referral=ReferralUrgency.IMMEDIATE,
            reasoning=f"Severe malnutrition: {', '.join(reasons)}. WHO IMCI p.14.",
        )

    # MODERATE MALNUTRITION
    # Source: IMCI Chart Booklet p.14, yellow row
    # MUAC 115-124mm
    if muac_mm is not None and muac_mm < MUAC_MODERATE_THRESHOLD_MM:
        return DomainClassification(
            classification=ClassificationType.MODERATE_MALNUTRITION,
            severity=Severity.YELLOW,
            referral=ReferralUrgency.WITHIN_24H,
            reasoning=f"Moderate malnutrition: MUAC {muac_mm}mm "
                      f"(threshold: {MUAC_MODERATE_THRESHOLD_MM}mm). WHO IMCI p.14.",
        )

    # NO MALNUTRITION
    return DomainClassification(
        classification=ClassificationType.NO_MALNUTRITION,
        severity=Severity.GREEN,
        referral=ReferralUrgency.NONE,
        reasoning="No malnutrition: no wasting, no edema"
                  + (f", MUAC {muac_mm}mm" if muac_mm else "")
                  + ". WHO IMCI p.14.",
    )


# ============================================================================
# HEART (MEMS — Pluggable) — Not standard IMCI
# ============================================================================

def classify_heart(
    *,
    age_months: int,
    estimated_bpm: int | None = None,
    abnormal_sounds: bool = False,
) -> DomainClassification | None:
    """Classify heart assessment (MEMS module — non-standard IMCI extension).

    This is a pluggable module. Returns None if no data provided.

    Args:
        age_months: Child's age in months.
        estimated_bpm: Estimated heart rate in beats per minute.
        abnormal_sounds: Whether abnormal heart sounds were detected.

    Returns:
        DomainClassification or None if no heart data.
    """
    if estimated_bpm is None and not abnormal_sounds:
        return None

    # Check for tachycardia or bradycardia
    if estimated_bpm is not None:
        threshold = (
            HEART_RATE_TACHYCARDIA_INFANT if age_months < 12
            else HEART_RATE_TACHYCARDIA_CHILD
        )

        if estimated_bpm > threshold or estimated_bpm < HEART_RATE_BRADYCARDIA:
            return DomainClassification(
                classification=ClassificationType.HEART_ABNORMALITY,
                severity=Severity.YELLOW,
                referral=ReferralUrgency.WITHIN_24H,
                reasoning=f"Heart rate {estimated_bpm} BPM outside normal range "
                          f"for age {age_months}mo. PALS guidelines.",
            )

    if abnormal_sounds:
        return DomainClassification(
            classification=ClassificationType.HEART_ABNORMALITY,
            severity=Severity.YELLOW,
            referral=ReferralUrgency.WITHIN_24H,
            reasoning="Abnormal heart sounds detected. Refer for evaluation.",
        )

    return DomainClassification(
        classification=ClassificationType.HEART_NORMAL,
        severity=Severity.GREEN,
        referral=ReferralUrgency.NONE,
        reasoning=f"Heart rate {estimated_bpm} BPM, normal for age {age_months}mo.",
    )


# ============================================================================
# AGGREGATE CLASSIFICATION
# ============================================================================

def classify_assessment(
    *,
    age_months: int,
    danger_signs: dict[str, Any] | None = None,
    breathing: dict[str, Any] | None = None,
    diarrhea: dict[str, Any] | None = None,
    fever: dict[str, Any] | None = None,
    nutrition: dict[str, Any] | None = None,
    heart: dict[str, Any] | None = None,
) -> AggregateClassification:
    """Run full IMCI classification across all domains.

    Takes structured findings from each domain and produces
    an aggregate classification with worst-severity determination.

    Args:
        age_months: Child's age in months (2-59).
        danger_signs: Dict of danger sign findings.
        breathing: Dict of breathing/cough findings.
        diarrhea: Dict of diarrhea/dehydration findings.
        fever: Dict of fever findings.
        nutrition: Dict of nutrition findings.
        heart: Dict of heart findings (optional, pluggable).

    Returns:
        AggregateClassification with all domain results and overall severity.
    """
    result = AggregateClassification()

    # 1. Danger signs (always first)
    if danger_signs is not None:
        danger_result = classify_danger_signs(**danger_signs)
        if danger_result is not None:
            result.classifications.append(danger_result)

    # 2. Breathing
    if breathing is not None:
        breathing_result = classify_breathing(age_months=age_months, **breathing)
        result.classifications.append(breathing_result)

    # 3. Diarrhea
    if diarrhea is not None:
        diarrhea_result = classify_diarrhea(**diarrhea)
        if diarrhea_result is not None:
            result.classifications.append(diarrhea_result)

    # 4. Fever
    if fever is not None:
        fever_result = classify_fever(**fever)
        if fever_result is not None:
            result.classifications.append(fever_result)

    # 5. Nutrition
    if nutrition is not None:
        nutrition_result = classify_nutrition(**nutrition)
        result.classifications.append(nutrition_result)

    # 6. Heart (pluggable)
    if heart is not None:
        heart_result = classify_heart(age_months=age_months, **heart)
        if heart_result is not None:
            result.classifications.append(heart_result)

    # If no classifications at all → healthy
    if not result.classifications:
        result.classifications.append(DomainClassification(
            classification=ClassificationType.HEALTHY,
            severity=Severity.GREEN,
            referral=ReferralUrgency.NONE,
            reasoning="No IMCI classifications triggered. Child appears healthy.",
        ))

    return result
