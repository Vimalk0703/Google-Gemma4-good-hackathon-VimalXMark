"""Shared type definitions for Malaika.

All enums, dataclasses, and type aliases used across modules live here.
This module has ZERO dependencies on other malaika modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# IMCI State Machine
# ---------------------------------------------------------------------------


class IMCIState(Enum):
    """States in the WHO IMCI assessment flow.

    Order matters — this is the mandatory protocol sequence.
    """

    DANGER_SIGNS = auto()
    BREATHING = auto()
    DIARRHEA = auto()
    FEVER = auto()
    NUTRITION = auto()
    HEART_MEMS = auto()
    CLASSIFY = auto()
    TREAT = auto()
    COMPLETE = auto()


# ---------------------------------------------------------------------------
# Severity & Classification
# ---------------------------------------------------------------------------


class Severity(Enum):
    """WHO IMCI severity classification — the traffic light system."""

    GREEN = "green"  # Home care
    YELLOW = "yellow"  # Specific treatment / referral within 24h
    RED = "red"  # Urgent referral — go NOW


class ReferralUrgency(Enum):
    """How urgently the child needs a health facility."""

    NONE = "none"  # Green — treat at home
    WITHIN_24H = "24h"  # Yellow — see a health worker within a day
    IMMEDIATE = "immediate"  # Red — transport to facility NOW


class ClassificationType(Enum):
    """Individual IMCI classifications that can be assigned."""

    # Danger signs
    URGENT_REFERRAL = "urgent_referral"

    # Breathing / Pneumonia
    SEVERE_PNEUMONIA = "severe_pneumonia"
    PNEUMONIA = "pneumonia"
    NO_PNEUMONIA_COUGH_OR_COLD = "no_pneumonia_cough_or_cold"

    # Diarrhea
    SEVERE_DEHYDRATION = "severe_dehydration"
    SOME_DEHYDRATION = "some_dehydration"
    NO_DEHYDRATION = "no_dehydration"
    SEVERE_PERSISTENT_DIARRHEA = "severe_persistent_diarrhea"
    PERSISTENT_DIARRHEA = "persistent_diarrhea"
    DYSENTERY = "dysentery"

    # Fever
    VERY_SEVERE_FEBRILE_DISEASE = "very_severe_febrile_disease"
    MALARIA = "malaria"
    FEVER_NO_MALARIA = "fever_no_malaria"
    MEASLES_WITH_COMPLICATIONS = "measles_with_complications"
    MEASLES = "measles"

    # Nutrition
    SEVERE_MALNUTRITION = "severe_malnutrition"
    MODERATE_MALNUTRITION = "moderate_malnutrition"  # Includes anemia
    NO_MALNUTRITION = "no_malnutrition"

    # Ear
    MASTOIDITIS = "mastoiditis"
    ACUTE_EAR_INFECTION = "acute_ear_infection"
    CHRONIC_EAR_INFECTION = "chronic_ear_infection"
    NO_EAR_INFECTION = "no_ear_infection"

    # Jaundice (neonatal extension)
    SEVERE_JAUNDICE = "severe_jaundice"
    JAUNDICE = "jaundice"

    # Heart (MEMS — pluggable)
    HEART_ABNORMALITY = "heart_abnormality"
    HEART_NORMAL = "heart_normal"

    # Healthy
    HEALTHY = "healthy"


# ---------------------------------------------------------------------------
# Finding Status (perception results)
# ---------------------------------------------------------------------------


class FindingStatus(Enum):
    """Status of a single clinical finding from AI perception."""

    DETECTED = "detected"  # AI found this sign with sufficient confidence
    NOT_DETECTED = "not_detected"  # AI checked and did not find this sign
    UNCERTAIN = "uncertain"  # AI couldn't determine — recommend human check
    NOT_ASSESSED = "not_assessed"  # Module skipped (disabled or unavailable)


# ---------------------------------------------------------------------------
# Perception Results (output of vision.py / audio.py)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PerceptionResult:
    """Base result from any AI perception call."""

    status: FindingStatus
    confidence: float  # 0.0 to 1.0
    description: str  # Human-readable description of what was observed
    raw_model_output: str  # Raw Gemma 4 output (for debugging/tracing)


@dataclass(frozen=True)
class BreathingRateResult(PerceptionResult):
    """Result of breathing rate analysis from video."""

    breath_count: int | None = None  # Breaths counted in the video
    duration_seconds: int = 15  # Duration of the video
    estimated_rate_per_minute: int | None = None  # Calculated rate


@dataclass(frozen=True)
class ChestAssessment(PerceptionResult):
    """Result of chest image analysis."""

    indrawing_detected: bool = False
    indrawing_location: str = ""  # "subcostal", "intercostal", "both"


@dataclass(frozen=True)
class BreathSoundAssessment(PerceptionResult):
    """Result of breath sound audio analysis."""

    wheeze: bool = False
    stridor: bool = False
    grunting: bool = False
    crackles: bool = False


@dataclass(frozen=True)
class SkinColorAssessment(PerceptionResult):
    """Result of skin color analysis from image."""

    jaundice_detected: bool = False
    cyanosis_detected: bool = False
    pallor_detected: bool = False


@dataclass(frozen=True)
class AlertnessAssessment(PerceptionResult):
    """Result of alertness/consciousness assessment from image."""

    is_alert: bool = True
    is_lethargic: bool = False
    is_unconscious: bool = False


@dataclass(frozen=True)
class NutritionAssessment(PerceptionResult):
    """Result of visible wasting / nutrition assessment from image."""

    visible_wasting: bool = False
    edema_detected: bool = False
    muac_mm: int | None = None  # Mid-upper arm circumference if provided


@dataclass(frozen=True)
class DehydrationAssessment(PerceptionResult):
    """Result of dehydration signs assessment from image."""

    sunken_eyes: bool = False
    skin_pinch_slow: bool = False  # Skin pinch goes back slowly
    skin_pinch_very_slow: bool = False  # Skin pinch goes back very slowly


@dataclass(frozen=True)
class HeartSoundAssessment(PerceptionResult):
    """Result of heart sound analysis (MEMS module)."""

    estimated_bpm: int | None = None
    abnormal_sounds: bool = False


@dataclass(frozen=True)
class SpeechUnderstanding(PerceptionResult):
    """Result of understanding caregiver's spoken response."""

    understood_text: str = ""  # What the model understood
    language_detected: str = ""  # Detected language
    intent: str = ""  # Parsed intent (e.g., "yes", "no", "3_days")


# ---------------------------------------------------------------------------
# Clinical Findings (per IMCI step)
# ---------------------------------------------------------------------------


@dataclass
class ClinicalFinding:
    """A single clinical finding at one IMCI step."""

    imci_state: IMCIState
    finding_status: FindingStatus
    perception_results: list[PerceptionResult] = field(default_factory=list)
    classifications: list[ClassificationType] = field(default_factory=list)
    notes: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=UTC))


# ---------------------------------------------------------------------------
# Treatment
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Treatment:
    """A single treatment instruction."""

    action: str  # What to do: "Give oral amoxicillin 250mg twice daily for 5 days"
    urgency: str  # "immediate", "before_referral", "at_home"
    category: str  # "antibiotic", "ors", "referral", "follow_up"


# ---------------------------------------------------------------------------
# Assessment Result (final output)
# ---------------------------------------------------------------------------


@dataclass
class AssessmentResult:
    """Complete result of a full IMCI assessment."""

    # Child info
    age_months: int
    language: str = "en"

    # Findings per step
    findings: list[ClinicalFinding] = field(default_factory=list)

    # Final classification
    classifications: list[ClassificationType] = field(default_factory=list)
    severity: Severity = Severity.GREEN
    referral_urgency: ReferralUrgency = ReferralUrgency.NONE

    # Treatment plan
    treatments: list[Treatment] = field(default_factory=list)
    treatment_text: str = ""  # Full treatment text in caregiver's language

    # Metadata
    started_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    completed_at: datetime | None = None
    model_used: str = ""
    prompt_versions: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Validated Input (output of guards)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValidatedInput:
    """Result of input guard validation — confirmed safe for processing."""

    file_path: Path
    media_type: str  # "image", "audio", "video"
    format_detected: str  # "JPEG", "PNG", "WAV", etc.
    size_bytes: int


@dataclass(frozen=True)
class ValidatedOutput:
    """Result of output guard validation — confirmed safe for clinical use."""

    status: str  # "valid", "uncertain", "invalid"
    parsed: dict[str, Any] = field(default_factory=dict)
    raw_output: str = ""
    retries_used: int = 0


# ---------------------------------------------------------------------------
# Observability
# ---------------------------------------------------------------------------


@dataclass
class StepTrace:
    """Trace record for a single IMCI step."""

    imci_state: IMCIState
    prompt_name: str
    prompt_version: str
    input_hash: str  # Hash of input media/text (not the actual data)
    raw_output: str  # Truncated model output
    parsed_result: str  # String repr of parsed PerceptionResult
    confidence: float
    latency_ms: float
    tokens_in: int = 0
    tokens_out: int = 0
    retries: int = 0
    cache_hit: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=UTC))


@dataclass
class AssessmentTrace:
    """Full trace of an IMCI assessment session."""

    session_id: str
    steps: list[StepTrace] = field(default_factory=list)
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    started_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    completed_at: datetime | None = None
