"""Vision perception module — image and video analysis using Gemma 4.

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
    AlertnessAssessment,
    BreathingRateResult,
    ChestAssessment,
    DehydrationAssessment,
    FindingStatus,
    NutritionAssessment,
    SkinColorAssessment,
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
# Vision Functions
# ---------------------------------------------------------------------------

def assess_alertness(
    image_path: Path,
    inference: MalaikaInference,
) -> AlertnessAssessment:
    """Assess child's alertness/consciousness from an image.

    Args:
        image_path: Path to the child's image (JPEG/PNG).
        inference: Loaded MalaikaInference instance.

    Returns:
        AlertnessAssessment with alertness level and confidence.
    """
    prompt = PromptRegistry.get("danger.assess_alertness")
    input_hash = _file_hash(image_path)

    try:
        raw_output, validated, retries = inference.analyze_image(
            image_path, prompt, input_hash=input_hash,
        )
    except Exception as e:
        logger.error("vision_alertness_failed", error=str(e))
        return AlertnessAssessment(
            status=FindingStatus.UNCERTAIN,
            confidence=0.0,
            description=f"Analysis failed: {e}",
            raw_model_output="",
        )

    parsed = validated.parsed
    status = _status_from_validated(validated)
    confidence = _confidence_from_parsed(parsed)

    alertness_level = parsed.get("alertness", "alert")
    is_alert = alertness_level == "alert"
    is_lethargic = alertness_level == "lethargic"
    is_unconscious = alertness_level == "unconscious"

    # If detecting danger signs, override status
    if is_lethargic or is_unconscious:
        if status == FindingStatus.UNCERTAIN:
            pass  # Keep uncertain — we are not confident
        # Status stays DETECTED since _status_from_validated handles "valid"

    return AlertnessAssessment(
        status=status,
        confidence=confidence,
        description=_description_from_parsed(parsed),
        raw_model_output=raw_output,
        is_alert=is_alert,
        is_lethargic=is_lethargic,
        is_unconscious=is_unconscious,
    )


def detect_chest_indrawing(
    image_path: Path,
    inference: MalaikaInference,
) -> ChestAssessment:
    """Detect chest indrawing from a chest image.

    Args:
        image_path: Path to chest image (JPEG/PNG).
        inference: Loaded MalaikaInference instance.

    Returns:
        ChestAssessment with indrawing detection and location.
    """
    prompt = PromptRegistry.get("breathing.detect_chest_indrawing")
    input_hash = _file_hash(image_path)

    try:
        raw_output, validated, retries = inference.analyze_image(
            image_path, prompt, input_hash=input_hash,
        )
    except Exception as e:
        logger.error("vision_chest_indrawing_failed", error=str(e))
        return ChestAssessment(
            status=FindingStatus.UNCERTAIN,
            confidence=0.0,
            description=f"Analysis failed: {e}",
            raw_model_output="",
        )

    parsed = validated.parsed
    status = _status_from_validated(validated)
    confidence = _confidence_from_parsed(parsed)

    indrawing = bool(parsed.get("indrawing_detected", False))
    location = str(parsed.get("location", ""))

    # Adjust status: if indrawing not detected, it's NOT_DETECTED, not DETECTED
    if status == FindingStatus.DETECTED and not indrawing:
        status = FindingStatus.NOT_DETECTED

    return ChestAssessment(
        status=status,
        confidence=confidence,
        description=_description_from_parsed(parsed),
        raw_model_output=raw_output,
        indrawing_detected=indrawing,
        indrawing_location=location,
    )


def assess_skin_color(
    image_path: Path,
    inference: MalaikaInference,
) -> SkinColorAssessment:
    """Assess skin color for jaundice, cyanosis, pallor from an image.

    Args:
        image_path: Path to child's image (JPEG/PNG).
        inference: Loaded MalaikaInference instance.

    Returns:
        SkinColorAssessment with detected color abnormalities.
    """
    prompt = PromptRegistry.get("danger.assess_skin_color")
    input_hash = _file_hash(image_path)

    try:
        raw_output, validated, retries = inference.analyze_image(
            image_path, prompt, input_hash=input_hash,
        )
    except Exception as e:
        logger.error("vision_skin_color_failed", error=str(e))
        return SkinColorAssessment(
            status=FindingStatus.UNCERTAIN,
            confidence=0.0,
            description=f"Analysis failed: {e}",
            raw_model_output="",
        )

    parsed = validated.parsed
    status = _status_from_validated(validated)
    confidence = _confidence_from_parsed(parsed)

    jaundice = bool(parsed.get("jaundice_detected", False))
    cyanosis = bool(parsed.get("cyanosis_detected", False))
    pallor = bool(parsed.get("pallor_detected", False))

    # If none detected, status is NOT_DETECTED
    if status == FindingStatus.DETECTED and not (jaundice or cyanosis or pallor):
        status = FindingStatus.NOT_DETECTED

    return SkinColorAssessment(
        status=status,
        confidence=confidence,
        description=_description_from_parsed(parsed),
        raw_model_output=raw_output,
        jaundice_detected=jaundice,
        cyanosis_detected=cyanosis,
        pallor_detected=pallor,
    )


def assess_wasting(
    image_path: Path,
    inference: MalaikaInference,
) -> NutritionAssessment:
    """Assess visible severe wasting from an image.

    Args:
        image_path: Path to child's image (JPEG/PNG).
        inference: Loaded MalaikaInference instance.

    Returns:
        NutritionAssessment with wasting detection.
    """
    prompt = PromptRegistry.get("nutrition.assess_wasting")
    input_hash = _file_hash(image_path)

    try:
        raw_output, validated, retries = inference.analyze_image(
            image_path, prompt, input_hash=input_hash,
        )
    except Exception as e:
        logger.error("vision_wasting_failed", error=str(e))
        return NutritionAssessment(
            status=FindingStatus.UNCERTAIN,
            confidence=0.0,
            description=f"Analysis failed: {e}",
            raw_model_output="",
        )

    parsed = validated.parsed
    status = _status_from_validated(validated)
    confidence = _confidence_from_parsed(parsed)

    wasting = bool(parsed.get("visible_severe_wasting", False))

    if status == FindingStatus.DETECTED and not wasting:
        status = FindingStatus.NOT_DETECTED

    return NutritionAssessment(
        status=status,
        confidence=confidence,
        description=_description_from_parsed(parsed),
        raw_model_output=raw_output,
        visible_wasting=wasting,
    )


def detect_edema(
    image_path: Path,
    inference: MalaikaInference,
) -> NutritionAssessment:
    """Detect bilateral pitting edema from an image of feet.

    Args:
        image_path: Path to image of child's feet (JPEG/PNG).
        inference: Loaded MalaikaInference instance.

    Returns:
        NutritionAssessment with edema detection.
    """
    prompt = PromptRegistry.get("nutrition.detect_edema")
    input_hash = _file_hash(image_path)

    try:
        raw_output, validated, retries = inference.analyze_image(
            image_path, prompt, input_hash=input_hash,
        )
    except Exception as e:
        logger.error("vision_edema_failed", error=str(e))
        return NutritionAssessment(
            status=FindingStatus.UNCERTAIN,
            confidence=0.0,
            description=f"Analysis failed: {e}",
            raw_model_output="",
        )

    parsed = validated.parsed
    status = _status_from_validated(validated)
    confidence = _confidence_from_parsed(parsed)

    edema = bool(parsed.get("edema_detected", False))
    bilateral = bool(parsed.get("bilateral", False))

    # IMCI requires bilateral edema
    edema_detected = edema and bilateral

    if status == FindingStatus.DETECTED and not edema_detected:
        status = FindingStatus.NOT_DETECTED

    return NutritionAssessment(
        status=status,
        confidence=confidence,
        description=_description_from_parsed(parsed),
        raw_model_output=raw_output,
        edema_detected=edema_detected,
    )


def assess_dehydration_signs(
    image_path: Path,
    inference: MalaikaInference,
) -> DehydrationAssessment:
    """Assess dehydration signs from an image (sunken eyes, skin pinch).

    Args:
        image_path: Path to child's image (JPEG/PNG).
        inference: Loaded MalaikaInference instance.

    Returns:
        DehydrationAssessment with dehydration sign detection.
    """
    prompt = PromptRegistry.get("diarrhea.assess_dehydration_signs")
    input_hash = _file_hash(image_path)

    try:
        raw_output, validated, retries = inference.analyze_image(
            image_path, prompt, input_hash=input_hash,
        )
    except Exception as e:
        logger.error("vision_dehydration_failed", error=str(e))
        return DehydrationAssessment(
            status=FindingStatus.UNCERTAIN,
            confidence=0.0,
            description=f"Analysis failed: {e}",
            raw_model_output="",
        )

    parsed = validated.parsed
    status = _status_from_validated(validated)
    confidence = _confidence_from_parsed(parsed)

    sunken_eyes = bool(parsed.get("sunken_eyes", False))

    skin_pinch_result = parsed.get("skin_pinch_result", "goes_back_immediately")
    skin_pinch_slow = skin_pinch_result == "goes_back_slowly"
    skin_pinch_very_slow = skin_pinch_result == "goes_back_very_slowly"

    has_signs = sunken_eyes or skin_pinch_slow or skin_pinch_very_slow
    if status == FindingStatus.DETECTED and not has_signs:
        status = FindingStatus.NOT_DETECTED

    return DehydrationAssessment(
        status=status,
        confidence=confidence,
        description=_description_from_parsed(parsed),
        raw_model_output=raw_output,
        sunken_eyes=sunken_eyes,
        skin_pinch_slow=skin_pinch_slow,
        skin_pinch_very_slow=skin_pinch_very_slow,
    )


def count_breathing_rate(
    video_path: Path,
    inference: MalaikaInference,
    duration_seconds: int = 15,
) -> BreathingRateResult:
    """Count breathing rate from a video of chest movement.

    Args:
        video_path: Path to video file (MP4/WEBM/AVI).
        inference: Loaded MalaikaInference instance.
        duration_seconds: Duration of the video in seconds.

    Returns:
        BreathingRateResult with breath count and estimated rate.
    """
    prompt = PromptRegistry.get("breathing.count_rate_from_video")
    input_hash = _file_hash(video_path)

    try:
        raw_output, validated, retries = inference.analyze_video(
            video_path, prompt, input_hash=input_hash,
            duration_seconds=duration_seconds,
        )
    except Exception as e:
        logger.error("vision_breathing_rate_failed", error=str(e))
        return BreathingRateResult(
            status=FindingStatus.UNCERTAIN,
            confidence=0.0,
            description=f"Analysis failed: {e}",
            raw_model_output="",
            duration_seconds=duration_seconds,
        )

    parsed = validated.parsed
    status = _status_from_validated(validated)
    confidence = _confidence_from_parsed(parsed)

    breath_count = parsed.get("breath_count")
    if isinstance(breath_count, (int, float)):
        breath_count = int(breath_count)
        estimated_rate = int((breath_count / duration_seconds) * 60)
    else:
        breath_count = None
        estimated_rate = None
        if status != FindingStatus.UNCERTAIN:
            status = FindingStatus.UNCERTAIN

    return BreathingRateResult(
        status=status,
        confidence=confidence,
        description=_description_from_parsed(parsed),
        raw_model_output=raw_output,
        breath_count=breath_count,
        duration_seconds=duration_seconds,
        estimated_rate_per_minute=estimated_rate,
    )
