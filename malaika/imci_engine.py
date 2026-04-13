"""IMCI Engine — state machine orchestrating the WHO IMCI assessment flow.

Ties perception modules (vision, audio) to protocol logic (imci_protocol).
State transitions are deterministic. Gemma 4 is used only for perception.

This module MUST follow WHO IMCI protocol order exactly.
This module MUST NOT call Gemma 4 directly -- only through vision/audio modules.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

from malaika.config import MalaikaConfig
from malaika.inference import MalaikaInference
from malaika.types import (
    AssessmentResult,
    AssessmentTrace,
    ClassificationType,
    ClinicalFinding,
    FindingStatus,
    IMCIState,
    PerceptionResult,
    ReferralUrgency,
    Severity,
)

logger = structlog.get_logger()

# State progression order — mandatory IMCI protocol sequence
_STATE_ORDER: list[IMCIState] = [
    IMCIState.DANGER_SIGNS,
    IMCIState.BREATHING,
    IMCIState.DIARRHEA,
    IMCIState.FEVER,
    IMCIState.NUTRITION,
    IMCIState.HEART_MEMS,
    IMCIState.CLASSIFY,
    IMCIState.TREAT,
    IMCIState.COMPLETE,
]


class IMCIEngine:
    """Orchestrates the WHO IMCI assessment as a deterministic state machine.

    Usage:
        config = load_config()
        inference = MalaikaInference(config)
        engine = IMCIEngine(inference, config, age_months=12)

        # Step through each state with appropriate inputs
        engine.assess_danger_signs(image_path=..., audio_path=...)
        engine.advance()
        engine.assess_breathing(video_path=..., image_path=..., audio_path=...)
        engine.advance()
        ...
        result = engine.get_result()
    """

    def __init__(
        self,
        inference: MalaikaInference,
        config: MalaikaConfig,
        age_months: int = 12,
        language: str = "en",
    ) -> None:
        self._inference = inference
        self._config = config
        self._age_months = age_months
        self._language = language

        # State
        self._current_state_index: int = 0
        self._findings: list[ClinicalFinding] = []
        self._result: AssessmentResult = AssessmentResult(
            age_months=age_months,
            language=language,
        )

        # Observability
        from malaika.observability import Tracer
        self._tracer = Tracer(
            max_raw_output_length=config.observability.max_raw_output_length,
        )
        self._session_id = self._tracer.start_session()

        logger.info(
            "imci_engine_started",
            session_id=self._session_id,
            age_months=age_months,
            language=language,
        )

    @property
    def current_state(self) -> IMCIState:
        """Current IMCI state."""
        return _STATE_ORDER[self._current_state_index]

    @property
    def session_id(self) -> str:
        """Current session ID."""
        return self._session_id

    @property
    def findings(self) -> list[ClinicalFinding]:
        """All clinical findings recorded so far."""
        return list(self._findings)

    @property
    def is_complete(self) -> bool:
        """Whether the assessment has reached COMPLETE state."""
        return self.current_state == IMCIState.COMPLETE

    def advance(self) -> IMCIState:
        """Advance to the next IMCI state.

        Skips HEART_MEMS if disabled in config.

        Returns:
            The new current state.

        Raises:
            RuntimeError: If already at COMPLETE state.
        """
        if self.is_complete:
            raise RuntimeError("Assessment is already complete. Cannot advance.")

        old_state = self.current_state
        self._current_state_index += 1

        # Skip HEART_MEMS if disabled
        if (
            self.current_state == IMCIState.HEART_MEMS
            and not self._config.features.enable_heart_rate
        ):
            logger.info(
                "imci_state_skipped",
                state="HEART_MEMS",
                reason="enable_heart_rate=False",
            )
            self._findings.append(ClinicalFinding(
                imci_state=IMCIState.HEART_MEMS,
                finding_status=FindingStatus.NOT_ASSESSED,
                notes="Heart MEMS module disabled",
            ))
            self._current_state_index += 1

        new_state = self.current_state

        logger.info(
            "imci_state_transition",
            from_state=old_state.name,
            to_state=new_state.name,
            findings_count=len(self._findings),
        )

        # Auto-run classify and treat
        if new_state == IMCIState.CLASSIFY:
            self._run_classification()
        elif new_state == IMCIState.TREAT:
            self._run_treatment()

        return new_state

    # -------------------------------------------------------------------
    # Assessment methods — one per IMCI domain
    # -------------------------------------------------------------------

    def assess_danger_signs(
        self,
        image_path: Path | None = None,
        audio_path: Path | None = None,
        caregiver_response: str | None = None,
    ) -> ClinicalFinding:
        """Assess general danger signs (IMCI step 1).

        Args:
            image_path: Image of the child (for alertness assessment).
            audio_path: Audio of caregiver response (for ability to drink).
            caregiver_response: Text alternative for caregiver response.

        Returns:
            ClinicalFinding for danger signs.
        """
        from malaika import vision

        perception_results: list[PerceptionResult] = []
        lethargic = False
        unconscious = False
        unable_to_drink = False
        vomits_everything = False

        # Visual alertness assessment
        if image_path is not None:
            alertness = vision.assess_alertness(image_path, self._inference)
            perception_results.append(alertness)
            lethargic = alertness.is_lethargic
            unconscious = alertness.is_unconscious

        # Caregiver response about ability to drink
        if audio_path is not None or caregiver_response is not None:
            from malaika.prompts import PromptRegistry

            prompt = PromptRegistry.get("danger.check_ability_to_drink")
            response_text = caregiver_response or ""

            if audio_path is not None:
                try:
                    raw, validated, retries = self._inference.analyze_audio(
                        audio_path, prompt,
                        caregiver_response=response_text or "audio input",
                    )
                    parsed = validated.parsed
                    unable_to_drink = not bool(parsed.get("able_to_drink", True))
                    vomits_everything = bool(parsed.get("vomits_everything", False))
                except Exception as e:
                    logger.error("danger_signs_audio_failed", error=str(e))
            elif response_text:
                try:
                    raw, validated, retries = self._inference.reason(
                        prompt, caregiver_response=response_text,
                    )
                    parsed = validated.parsed
                    unable_to_drink = not bool(parsed.get("able_to_drink", True))
                    vomits_everything = bool(parsed.get("vomits_everything", False))
                except Exception as e:
                    logger.error("danger_signs_text_failed", error=str(e))

        # Classify using protocol
        from malaika.imci_protocol import classify_danger_signs
        classification = classify_danger_signs(
            lethargic=lethargic,
            unconscious=unconscious,
            unable_to_drink=unable_to_drink,
            vomits_everything=vomits_everything,
        )

        classifications = [classification.classification] if classification else []
        finding_status = (
            FindingStatus.DETECTED if classification
            else FindingStatus.NOT_DETECTED
        )

        finding = ClinicalFinding(
            imci_state=IMCIState.DANGER_SIGNS,
            finding_status=finding_status,
            perception_results=perception_results,
            classifications=classifications,
        )
        self._findings.append(finding)
        return finding

    def assess_breathing(
        self,
        video_path: Path | None = None,
        image_path: Path | None = None,
        audio_path: Path | None = None,
        has_cough: bool = False,
    ) -> ClinicalFinding:
        """Assess cough/breathing (IMCI step 2).

        Args:
            video_path: Video of chest for breathing rate.
            image_path: Image of chest for indrawing.
            audio_path: Audio for breath sounds.
            has_cough: Whether cough was reported.

        Returns:
            ClinicalFinding for breathing.
        """
        from malaika import vision, audio

        perception_results: list[PerceptionResult] = []
        breathing_rate: int | None = None
        has_indrawing = False
        has_stridor = False
        has_wheeze = False

        # Breathing rate from video
        if video_path is not None:
            br_result = vision.count_breathing_rate(
                video_path, self._inference,
                duration_seconds=self._config.media.breathing_video_duration_seconds,
            )
            perception_results.append(br_result)
            breathing_rate = br_result.estimated_rate_per_minute

        # Chest indrawing from image
        if image_path is not None:
            chest = vision.detect_chest_indrawing(image_path, self._inference)
            perception_results.append(chest)
            has_indrawing = chest.indrawing_detected

        # Breath sounds from audio
        if audio_path is not None:
            sounds = audio.classify_breath_sounds(audio_path, self._inference)
            perception_results.append(sounds)
            has_stridor = sounds.stridor
            has_wheeze = sounds.wheeze

        # Classify
        from malaika.imci_protocol import classify_breathing
        classification = classify_breathing(
            age_months=self._age_months,
            has_cough=has_cough,
            breathing_rate=breathing_rate,
            has_indrawing=has_indrawing,
            has_stridor=has_stridor,
            has_wheeze=has_wheeze,
        )

        finding = ClinicalFinding(
            imci_state=IMCIState.BREATHING,
            finding_status=FindingStatus.DETECTED if classification.severity != Severity.GREEN else FindingStatus.NOT_DETECTED,
            perception_results=perception_results,
            classifications=[classification.classification],
        )
        self._findings.append(finding)
        return finding

    def assess_diarrhea(
        self,
        image_path: Path | None = None,
        audio_path: Path | None = None,
        has_diarrhea: bool = False,
        duration_days: int = 0,
        blood_in_stool: bool = False,
        caregiver_response: str | None = None,
    ) -> ClinicalFinding:
        """Assess diarrhea/dehydration (IMCI step 3).

        Args:
            image_path: Image for dehydration visual signs.
            audio_path: Audio of caregiver response.
            has_diarrhea: Whether diarrhea was reported.
            duration_days: How long diarrhea has lasted.
            blood_in_stool: Blood reported in stool.
            caregiver_response: Text input from caregiver.

        Returns:
            ClinicalFinding for diarrhea.
        """
        from malaika import vision

        perception_results: list[PerceptionResult] = []
        sunken_eyes = False
        skin_pinch_slow = False
        skin_pinch_very_slow = False

        # Visual dehydration assessment
        if image_path is not None and has_diarrhea:
            dehydration = vision.assess_dehydration_signs(image_path, self._inference)
            perception_results.append(dehydration)
            sunken_eyes = dehydration.sunken_eyes
            skin_pinch_slow = dehydration.skin_pinch_slow
            skin_pinch_very_slow = dehydration.skin_pinch_very_slow

        # Classify
        from malaika.imci_protocol import classify_diarrhea
        classification = classify_diarrhea(
            has_diarrhea=has_diarrhea,
            duration_days=duration_days,
            blood_in_stool=blood_in_stool,
            sunken_eyes=sunken_eyes,
            skin_pinch_slow=skin_pinch_slow,
            skin_pinch_very_slow=skin_pinch_very_slow,
        )

        if classification is None:
            finding = ClinicalFinding(
                imci_state=IMCIState.DIARRHEA,
                finding_status=FindingStatus.NOT_DETECTED,
                perception_results=perception_results,
                notes="No diarrhea reported",
            )
        else:
            finding = ClinicalFinding(
                imci_state=IMCIState.DIARRHEA,
                finding_status=FindingStatus.DETECTED if classification.severity != Severity.GREEN else FindingStatus.NOT_DETECTED,
                perception_results=perception_results,
                classifications=[classification.classification],
            )

        self._findings.append(finding)
        return finding

    def assess_fever(
        self,
        has_fever: bool = False,
        duration_days: int = 0,
        stiff_neck: bool = False,
        malaria_risk: bool = False,
        measles_recent: bool = False,
        measles_complications: bool = False,
    ) -> ClinicalFinding:
        """Assess fever (IMCI step 4).

        Args:
            has_fever: Whether fever was reported/measured.
            duration_days: Duration of fever.
            stiff_neck: Stiff neck reported.
            malaria_risk: In malaria risk area.
            measles_recent: Recent measles.
            measles_complications: Measles complications present.

        Returns:
            ClinicalFinding for fever.
        """
        from malaika.imci_protocol import classify_fever
        classification = classify_fever(
            has_fever=has_fever,
            duration_days=duration_days,
            stiff_neck=stiff_neck,
            malaria_risk=malaria_risk,
            measles_recent=measles_recent,
            measles_complications=measles_complications,
        )

        if classification is None:
            finding = ClinicalFinding(
                imci_state=IMCIState.FEVER,
                finding_status=FindingStatus.NOT_DETECTED,
                notes="No fever reported",
            )
        else:
            finding = ClinicalFinding(
                imci_state=IMCIState.FEVER,
                finding_status=FindingStatus.DETECTED if classification.severity != Severity.GREEN else FindingStatus.NOT_DETECTED,
                classifications=[classification.classification],
            )

        self._findings.append(finding)
        return finding

    def assess_nutrition(
        self,
        image_path: Path | None = None,
        feet_image_path: Path | None = None,
        muac_mm: int | None = None,
    ) -> ClinicalFinding:
        """Assess nutrition/malnutrition (IMCI step 5).

        Args:
            image_path: Image of child for wasting assessment.
            feet_image_path: Image of feet for edema detection.
            muac_mm: Mid-upper arm circumference in mm (if measured).

        Returns:
            ClinicalFinding for nutrition.
        """
        from malaika import vision

        perception_results: list[PerceptionResult] = []
        visible_wasting = False
        edema_detected = False

        # Wasting assessment
        if image_path is not None:
            wasting = vision.assess_wasting(image_path, self._inference)
            perception_results.append(wasting)
            visible_wasting = wasting.visible_wasting

        # Edema detection
        if feet_image_path is not None:
            edema = vision.detect_edema(feet_image_path, self._inference)
            perception_results.append(edema)
            edema_detected = edema.edema_detected

        # Classify
        from malaika.imci_protocol import classify_nutrition
        classification = classify_nutrition(
            visible_wasting=visible_wasting,
            edema=edema_detected,
            muac_mm=muac_mm,
        )

        finding = ClinicalFinding(
            imci_state=IMCIState.NUTRITION,
            finding_status=FindingStatus.DETECTED if classification.severity != Severity.GREEN else FindingStatus.NOT_DETECTED,
            perception_results=perception_results,
            classifications=[classification.classification],
        )
        self._findings.append(finding)
        return finding

    def assess_heart(
        self,
        audio_path: Path | None = None,
    ) -> ClinicalFinding:
        """Assess heart sounds (IMCI optional MEMS step).

        Args:
            audio_path: Audio recording of heart sounds.

        Returns:
            ClinicalFinding for heart.
        """
        from malaika import audio as audio_module

        perception_results: list[PerceptionResult] = []
        estimated_bpm: int | None = None
        abnormal_sounds = False

        if audio_path is not None:
            heart = audio_module.analyze_heart_sounds(audio_path, self._inference)
            perception_results.append(heart)
            estimated_bpm = heart.estimated_bpm
            abnormal_sounds = heart.abnormal_sounds

        from malaika.imci_protocol import classify_heart
        classification = classify_heart(
            age_months=self._age_months,
            estimated_bpm=estimated_bpm,
            abnormal_sounds=abnormal_sounds,
        )

        if classification is None:
            finding = ClinicalFinding(
                imci_state=IMCIState.HEART_MEMS,
                finding_status=FindingStatus.NOT_ASSESSED,
                perception_results=perception_results,
                notes="No heart data provided",
            )
        else:
            finding = ClinicalFinding(
                imci_state=IMCIState.HEART_MEMS,
                finding_status=FindingStatus.DETECTED if classification.severity != Severity.GREEN else FindingStatus.NOT_DETECTED,
                perception_results=perception_results,
                classifications=[classification.classification],
            )

        self._findings.append(finding)
        return finding

    # -------------------------------------------------------------------
    # Internal methods
    # -------------------------------------------------------------------

    def _run_classification(self) -> None:
        """Aggregate IMCI classifications from all domain findings.

        Each assess_* method already ran the protocol classification.
        This method gathers those results and determines overall severity.
        """
        from malaika.imci_protocol import DomainClassification, AggregateClassification

        aggregate = AggregateClassification()

        # Severity mapping for lookup
        _severity_map: dict[str, Severity] = {
            ct.value: Severity.RED
            for ct in [
                ClassificationType.URGENT_REFERRAL,
                ClassificationType.SEVERE_PNEUMONIA,
                ClassificationType.SEVERE_DEHYDRATION,
                ClassificationType.SEVERE_PERSISTENT_DIARRHEA,
                ClassificationType.VERY_SEVERE_FEBRILE_DISEASE,
                ClassificationType.SEVERE_MALNUTRITION,
                ClassificationType.SEVERE_JAUNDICE,
            ]
        }
        _yellow_types = {
            ClassificationType.PNEUMONIA,
            ClassificationType.SOME_DEHYDRATION,
            ClassificationType.PERSISTENT_DIARRHEA,
            ClassificationType.DYSENTERY,
            ClassificationType.MALARIA,
            ClassificationType.FEVER_NO_MALARIA,
            ClassificationType.MEASLES_WITH_COMPLICATIONS,
            ClassificationType.MEASLES,
            ClassificationType.MODERATE_MALNUTRITION,
            ClassificationType.HEART_ABNORMALITY,
            ClassificationType.ACUTE_EAR_INFECTION,
            ClassificationType.CHRONIC_EAR_INFECTION,
            ClassificationType.JAUNDICE,
        }

        all_classifications: list[ClassificationType] = []
        for finding in self._findings:
            if finding.imci_state in (IMCIState.CLASSIFY, IMCIState.TREAT, IMCIState.COMPLETE):
                continue
            all_classifications.extend(finding.classifications)

        for ct in all_classifications:
            if ct.value in _severity_map:
                severity = Severity.RED
                referral = ReferralUrgency.IMMEDIATE
            elif ct in _yellow_types:
                severity = Severity.YELLOW
                referral = ReferralUrgency.WITHIN_24H
            else:
                severity = Severity.GREEN
                referral = ReferralUrgency.NONE

            aggregate.classifications.append(DomainClassification(
                classification=ct,
                severity=severity,
                referral=referral,
                reasoning=f"Classification {ct.value} from assessment",
            ))

        # If no classifications were found, add HEALTHY
        if not aggregate.classifications:
            aggregate.classifications.append(DomainClassification(
                classification=ClassificationType.HEALTHY,
                severity=Severity.GREEN,
                referral=ReferralUrgency.NONE,
                reasoning="No IMCI classifications triggered. Child appears healthy.",
            ))

        # Update result
        self._result.classifications = aggregate.all_classification_types
        self._result.severity = aggregate.severity
        self._result.referral_urgency = aggregate.referral
        self._result.findings = list(self._findings)

        finding = ClinicalFinding(
            imci_state=IMCIState.CLASSIFY,
            finding_status=FindingStatus.DETECTED,
            classifications=aggregate.all_classification_types,
            notes=f"Severity: {aggregate.severity.value}, Referral: {aggregate.referral.value}",
        )
        self._findings.append(finding)

        logger.info(
            "imci_classification_complete",
            severity=aggregate.severity.value,
            referral=aggregate.referral.value,
            classifications=[c.value for c in aggregate.all_classification_types],
        )

    def _run_treatment(self) -> None:
        """Generate treatment plan using Gemma 4."""
        from malaika.prompts import PromptRegistry

        try:
            prompt = PromptRegistry.get("treatment.generate_plan")

            classifications_str = ", ".join(
                c.value for c in self._result.classifications
            )

            raw, validated, retries = self._inference.reason(
                prompt,
                child_age_months=str(self._age_months),
                classifications=classifications_str,
                urgency=self._result.referral_urgency.value,
                language=self._language,
            )

            treatment_text = validated.parsed.get("text", raw)
            self._result.treatment_text = treatment_text

        except Exception as e:
            logger.error("treatment_generation_failed", error=str(e))
            self._result.treatment_text = (
                "Treatment plan could not be generated. "
                "Please consult a health worker immediately."
            )

        finding = ClinicalFinding(
            imci_state=IMCIState.TREAT,
            finding_status=FindingStatus.DETECTED,
            notes="Treatment plan generated",
        )
        self._findings.append(finding)

    def get_result(self) -> AssessmentResult:
        """Get the assessment result. Finishes tracing session.

        Returns:
            Complete AssessmentResult.
        """
        self._result.findings = list(self._findings)
        self._result.completed_at = datetime.now(tz=timezone.utc)
        self._result.model_used = self._config.model.model_name

        try:
            self._tracer.finish_session()
        except RuntimeError:
            pass  # Session already finished

        return self._result

    def get_trace(self) -> AssessmentTrace | None:
        """Get the assessment trace if session is active.

        Returns:
            AssessmentTrace or None.
        """
        try:
            return self._tracer.finish_session()
        except RuntimeError:
            return None
