"""Malaika Gradio UI — entry point for judges to interact with.

Provides a step-by-step IMCI assessment interface with:
- Tab 1: Assessment — guided flow through IMCI protocol steps
- Tab 2: Results — full assessment summary and treatment plan

Run with: python -m malaika.app
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog

from malaika.config import MalaikaConfig, load_config
from malaika.tts import MalaikaTTS
from malaika.types import (
    ClinicalFinding,
    IMCIState,
    Severity,
)

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BANNER = (
    "**Malaika** (Angel in Swahili) -- WHO IMCI Child Survival AI powered by Gemma 4\n\n"
    "Demo for Gemma 4 Good Hackathon -- **not for clinical use**"
)

# Human-readable state labels and descriptions
_STATE_LABELS: dict[IMCIState, str] = {
    IMCIState.DANGER_SIGNS: "Danger Signs",
    IMCIState.BREATHING: "Breathing Assessment",
    IMCIState.DIARRHEA: "Diarrhea / Dehydration",
    IMCIState.FEVER: "Fever Assessment",
    IMCIState.NUTRITION: "Nutrition Assessment",
    IMCIState.HEART_MEMS: "Heart Sounds (MEMS)",
    IMCIState.CLASSIFY: "Classification",
    IMCIState.TREAT: "Treatment Plan",
    IMCIState.COMPLETE: "Assessment Complete",
}

_STATE_DESCRIPTIONS: dict[IMCIState, str] = {
    IMCIState.DANGER_SIGNS: (
        "Check for general danger signs: Is the child lethargic or unconscious? "
        "Can the child drink or breastfeed? Upload a photo of the child and/or "
        "enter caregiver responses."
    ),
    IMCIState.BREATHING: (
        "Assess cough and breathing: Upload a 15-second video of the child's chest "
        "for breathing rate, a chest image for indrawing, and/or audio for breath sounds."
    ),
    IMCIState.DIARRHEA: (
        "Assess diarrhea and dehydration: Upload an image for skin pinch / sunken eyes. "
        "Enter caregiver reports about diarrhea duration and blood in stool."
    ),
    IMCIState.FEVER: (
        "Assess fever: Enter caregiver reports about fever, duration, stiff neck, "
        "malaria risk area, and recent measles."
    ),
    IMCIState.NUTRITION: (
        "Assess nutrition: Upload a photo of the child for visible wasting assessment. "
        "Enter MUAC measurement if available."
    ),
    IMCIState.HEART_MEMS: (
        "Optional heart assessment: Upload audio of heart sounds recorded with "
        "a digital stethoscope or phone microphone."
    ),
    IMCIState.CLASSIFY: "Malaika is classifying findings using WHO IMCI protocol...",
    IMCIState.TREAT: "Generating treatment plan...",
    IMCIState.COMPLETE: "Assessment complete. Review results below.",
}

_SEVERITY_COLORS: dict[Severity, str] = {
    Severity.GREEN: "#28a745",
    Severity.YELLOW: "#ffc107",
    Severity.RED: "#dc3545",
}

_SEVERITY_EMOJI: dict[Severity, str] = {
    Severity.GREEN: "GREEN",
    Severity.YELLOW: "YELLOW",
    Severity.RED: "RED",
}


# ---------------------------------------------------------------------------
# App State Management
# ---------------------------------------------------------------------------

class AppState:
    """Manages the Gradio app state for one assessment session."""

    def __init__(self, config: MalaikaConfig) -> None:
        self.config = config
        self.engine: Any = None
        self.inference: Any = None
        self.tts = MalaikaTTS(config)
        self.model_loaded = False
        self.model_error: str | None = None
        self._step_index = 0

    @property
    def current_state(self) -> IMCIState:
        """Current IMCI state from the engine, or DANGER_SIGNS if no engine."""
        if self.engine is not None:
            return self.engine.current_state
        return IMCIState.DANGER_SIGNS

    @property
    def step_number(self) -> int:
        """1-based step number for the current state."""
        return self._step_index + 1

    @property
    def total_steps(self) -> int:
        """Total number of assessment steps (excluding auto-steps)."""
        total = 5  # DANGER_SIGNS through NUTRITION
        if self.config.features.enable_heart_rate:
            total += 1
        return total

    def progress_text(self) -> str:
        """Progress indicator text."""
        state = self.current_state
        label = _STATE_LABELS.get(state, state.name)
        if state in (IMCIState.CLASSIFY, IMCIState.TREAT, IMCIState.COMPLETE):
            return f"Step {self.total_steps} of {self.total_steps}: {label}"
        return f"Step {self.step_number} of {self.total_steps}: {label}"

    def load_model(self) -> str:
        """Attempt to load the Gemma 4 model. Returns status message."""
        try:
            from malaika.inference import MalaikaInference

            self.inference = MalaikaInference(self.config)
            self.inference.load_model()
            self.model_loaded = True
            self.model_error = None
            return (
                f"Model loaded successfully on {self.inference.device}. "
                f"Ready for assessment."
            )
        except Exception as exc:
            self.model_error = str(exc)
            self.model_loaded = False
            logger.error("model_load_failed", error=str(exc))
            return (
                f"Model loading failed: {exc}\n\n"
                f"The app will run in demo mode with limited functionality. "
                f"For full assessment, ensure GPU is available and model is downloaded."
            )

    def start_assessment(self, age_months: int, language: str) -> str:
        """Start a new IMCI assessment session."""
        if not self.model_loaded or self.inference is None:
            return (
                "Cannot start assessment: model not loaded. "
                "Please check the model status above."
            )

        try:
            from malaika.imci_engine import IMCIEngine

            self.engine = IMCIEngine(
                self.inference, self.config,
                age_months=age_months, language=language,
            )
            self._step_index = 0
            return f"Assessment started for {age_months}-month-old child (language: {language})."
        except Exception as exc:
            logger.error("assessment_start_failed", error=str(exc))
            return f"Failed to start assessment: {exc}"

    def advance(self) -> str:
        """Advance to next IMCI state."""
        if self.engine is None:
            return "No assessment in progress."
        if self.engine.is_complete:
            return "Assessment already complete."

        try:
            self._step_index += 1
            new_state = self.engine.advance()
            return f"Advanced to: {_STATE_LABELS.get(new_state, new_state.name)}"
        except RuntimeError as exc:
            return f"Cannot advance: {exc}"


# ---------------------------------------------------------------------------
# UI Builder Functions
# ---------------------------------------------------------------------------

def _severity_badge(severity: Severity) -> str:
    """Create an HTML badge for severity level."""
    color = _SEVERITY_COLORS[severity]
    label = _SEVERITY_EMOJI[severity]
    return (
        f'<span style="background-color:{color};color:white;padding:4px 12px;'
        f'border-radius:4px;font-weight:bold;font-size:1.1em;">'
        f'{label}</span>'
    )


def _finding_to_markdown(finding: ClinicalFinding) -> str:
    """Convert a ClinicalFinding to markdown text."""
    state_label = _STATE_LABELS.get(finding.imci_state, finding.imci_state.name)
    status = finding.finding_status.value.replace("_", " ").title()
    classifications = ", ".join(c.value.replace("_", " ").title() for c in finding.classifications)

    lines = [f"### {state_label}"]
    lines.append(f"- **Status**: {status}")
    if classifications:
        lines.append(f"- **Classifications**: {classifications}")
    if finding.notes:
        lines.append(f"- **Notes**: {finding.notes}")

    # Confidence from perception results
    for pr in finding.perception_results:
        lines.append(f"- **Confidence**: {pr.confidence:.0%}")
        if pr.description:
            lines.append(f"- **Observation**: {pr.description}")

    return "\n".join(lines)


def _build_results_markdown(app_state: AppState) -> str:
    """Build full results markdown from the completed assessment."""
    if app_state.engine is None:
        return "No assessment has been run yet."

    result = app_state.engine.get_result()

    lines: list[str] = []
    lines.append("# Assessment Results\n")

    # Severity banner
    lines.append(f"## Overall Severity: {_severity_badge(result.severity)}\n")

    # Referral urgency
    referral_text = {
        "none": "No referral needed -- home care",
        "24h": "See a health worker within 24 hours",
        "immediate": "URGENT: Transport to health facility immediately",
    }
    lines.append(
        f"**Referral**: {referral_text.get(result.referral_urgency.value, result.referral_urgency.value)}\n"
    )

    # Classifications
    lines.append("## Classifications\n")
    for ct in result.classifications:
        label = ct.value.replace("_", " ").title()
        lines.append(f"- {label}")
    lines.append("")

    # Findings per step
    lines.append("## Findings by Step\n")
    for finding in result.findings:
        if finding.imci_state in (IMCIState.CLASSIFY, IMCIState.TREAT, IMCIState.COMPLETE):
            continue
        lines.append(_finding_to_markdown(finding))
        lines.append("")

    # Treatment
    if result.treatment_text:
        lines.append("## Treatment Plan\n")
        lines.append(result.treatment_text)
        lines.append("")

    # Metadata
    lines.append("---")
    lines.append(f"*Age: {result.age_months} months | Language: {result.language} | "
                 f"Model: {result.model_used}*")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Gradio App Factory
# ---------------------------------------------------------------------------

def create_app(config: MalaikaConfig | None = None) -> Any:
    """Create and return the Gradio Blocks app.

    Args:
        config: Optional MalaikaConfig override. Uses load_config() if None.

    Returns:
        Gradio Blocks app instance.
    """
    try:
        import gradio as gr  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError(
            "Gradio is required for the UI. Install with: pip install gradio"
        ) from exc

    if config is None:
        config = load_config()

    app_state = AppState(config)

    # ------------------------------------------------------------------
    # Event handler functions
    # ------------------------------------------------------------------

    def on_load_model() -> tuple[str, str]:
        """Load model on button click."""
        status = app_state.load_model()
        return status, app_state.progress_text()

    def on_start_assessment(
        age_months: int, language: str,
    ) -> tuple[str, str, str, str]:
        """Start a new assessment."""
        age = max(2, min(59, int(age_months)))
        msg = app_state.start_assessment(age, language)
        state = app_state.current_state
        desc = _STATE_DESCRIPTIONS.get(state, "")
        progress = app_state.progress_text()
        return msg, desc, progress, _get_input_visibility(state)

    def on_assess_danger_signs(
        image: str | None,
        caregiver_text: str,
    ) -> tuple[str, str]:
        """Run danger signs assessment."""
        if app_state.engine is None:
            return "No assessment in progress. Start one first.", ""

        if app_state.current_state != IMCIState.DANGER_SIGNS:
            return f"Not on danger signs step (current: {app_state.current_state.name}).", ""

        try:
            image_path = Path(image) if image else None
            finding = app_state.engine.assess_danger_signs(
                image_path=image_path,
                caregiver_response=caregiver_text or None,
            )
            return _finding_to_markdown(finding), ""
        except Exception as exc:
            logger.error("assess_danger_signs_failed", error=str(exc))
            return f"Assessment error: {exc}", ""

    def on_assess_breathing(
        video: str | None,
        image: str | None,
        audio: str | None,
        has_cough: bool,
    ) -> tuple[str, str]:
        """Run breathing assessment."""
        if app_state.engine is None:
            return "No assessment in progress.", ""

        if app_state.current_state != IMCIState.BREATHING:
            return f"Not on breathing step (current: {app_state.current_state.name}).", ""

        try:
            finding = app_state.engine.assess_breathing(
                video_path=Path(video) if video else None,
                image_path=Path(image) if image else None,
                audio_path=Path(audio) if audio else None,
                has_cough=has_cough,
            )
            return _finding_to_markdown(finding), ""
        except Exception as exc:
            logger.error("assess_breathing_failed", error=str(exc))
            return f"Assessment error: {exc}", ""

    def on_assess_diarrhea(
        image: str | None,
        has_diarrhea: bool,
        duration_days: int,
        blood_in_stool: bool,
        caregiver_text: str,
    ) -> tuple[str, str]:
        """Run diarrhea assessment."""
        if app_state.engine is None:
            return "No assessment in progress.", ""

        if app_state.current_state != IMCIState.DIARRHEA:
            return f"Not on diarrhea step (current: {app_state.current_state.name}).", ""

        try:
            finding = app_state.engine.assess_diarrhea(
                image_path=Path(image) if image else None,
                has_diarrhea=has_diarrhea,
                duration_days=int(duration_days),
                blood_in_stool=blood_in_stool,
                caregiver_response=caregiver_text or None,
            )
            return _finding_to_markdown(finding), ""
        except Exception as exc:
            logger.error("assess_diarrhea_failed", error=str(exc))
            return f"Assessment error: {exc}", ""

    def on_assess_fever(
        has_fever: bool,
        duration_days: int,
        stiff_neck: bool,
        malaria_risk: bool,
        measles_recent: bool,
        measles_complications: bool,
    ) -> tuple[str, str]:
        """Run fever assessment."""
        if app_state.engine is None:
            return "No assessment in progress.", ""

        if app_state.current_state != IMCIState.FEVER:
            return f"Not on fever step (current: {app_state.current_state.name}).", ""

        try:
            finding = app_state.engine.assess_fever(
                has_fever=has_fever,
                duration_days=int(duration_days),
                stiff_neck=stiff_neck,
                malaria_risk=malaria_risk,
                measles_recent=measles_recent,
                measles_complications=measles_complications,
            )
            return _finding_to_markdown(finding), ""
        except Exception as exc:
            logger.error("assess_fever_failed", error=str(exc))
            return f"Assessment error: {exc}", ""

    def on_assess_nutrition(
        image: str | None,
        muac_mm: int | None,
    ) -> tuple[str, str]:
        """Run nutrition assessment."""
        if app_state.engine is None:
            return "No assessment in progress.", ""

        if app_state.current_state != IMCIState.NUTRITION:
            return f"Not on nutrition step (current: {app_state.current_state.name}).", ""

        try:
            muac = int(muac_mm) if muac_mm and muac_mm > 0 else None
            finding = app_state.engine.assess_nutrition(
                image_path=Path(image) if image else None,
                muac_mm=muac,
            )
            return _finding_to_markdown(finding), ""
        except Exception as exc:
            logger.error("assess_nutrition_failed", error=str(exc))
            return f"Assessment error: {exc}", ""

    def on_assess_heart(
        audio: str | None,
    ) -> tuple[str, str]:
        """Run heart assessment."""
        if app_state.engine is None:
            return "No assessment in progress.", ""

        if app_state.current_state != IMCIState.HEART_MEMS:
            return f"Not on heart step (current: {app_state.current_state.name}).", ""

        try:
            finding = app_state.engine.assess_heart(
                audio_path=Path(audio) if audio else None,
            )
            return _finding_to_markdown(finding), ""
        except Exception as exc:
            logger.error("assess_heart_failed", error=str(exc))
            return f"Assessment error: {exc}", ""

    def on_next_step() -> tuple[str, str, str, str]:
        """Advance to the next IMCI step."""
        msg = app_state.advance()
        state = app_state.current_state
        desc = _STATE_DESCRIPTIONS.get(state, "")
        progress = app_state.progress_text()
        visibility = _get_input_visibility(state)
        return msg, desc, progress, visibility

    def on_generate_tts(text: str, language: str) -> str | None:
        """Generate TTS audio for treatment text."""
        if not text.strip():
            return None
        wav = app_state.tts.speak(text, language=language)
        return str(wav) if wav else None

    def on_view_results() -> str:
        """Generate results markdown."""
        return _build_results_markdown(app_state)

    def _get_input_visibility(state: IMCIState) -> str:
        """Return which input group should be visible for this state."""
        visibility_map: dict[IMCIState, str] = {
            IMCIState.DANGER_SIGNS: "danger_signs",
            IMCIState.BREATHING: "breathing",
            IMCIState.DIARRHEA: "diarrhea",
            IMCIState.FEVER: "fever",
            IMCIState.NUTRITION: "nutrition",
            IMCIState.HEART_MEMS: "heart",
        }
        return visibility_map.get(state, "none")

    # ------------------------------------------------------------------
    # Build the Gradio Blocks UI
    # ------------------------------------------------------------------

    with gr.Blocks(
        title="Malaika -- WHO IMCI Child Health AI",
        theme=gr.themes.Soft(),
        css="""
            .severity-red { background-color: #dc3545 !important; }
            .severity-yellow { background-color: #ffc107 !important; }
            .severity-green { background-color: #28a745 !important; }
            .banner { text-align: center; padding: 10px; }
            .step-header { font-size: 1.2em; font-weight: bold; }
        """,
    ) as app:

        # Banner
        gr.Markdown(_BANNER, elem_classes=["banner"])

        with gr.Tabs():

            # ============================================================
            # TAB 1: Assessment
            # ============================================================

            with gr.Tab("Assessment"):

                # Model status and controls
                with gr.Row():
                    with gr.Column(scale=2):
                        model_status = gr.Textbox(
                            label="Model Status",
                            value="Model not loaded. Click 'Load Model' to start.",
                            interactive=False,
                            lines=2,
                        )
                    with gr.Column(scale=1):
                        load_model_btn = gr.Button(
                            "Load Model",
                            variant="primary",
                            size="lg",
                        )

                gr.Markdown("---")

                # Assessment setup
                with gr.Row():
                    age_input = gr.Slider(
                        minimum=2, maximum=59, value=12, step=1,
                        label="Child's Age (months)",
                        info="WHO IMCI covers ages 2-59 months",
                    )
                    language_input = gr.Dropdown(
                        choices=["en", "sw", "hi", "fr"],
                        value="en",
                        label="Language",
                        info="Language for treatment instructions",
                    )
                    start_btn = gr.Button(
                        "Start New Assessment",
                        variant="primary",
                    )

                # Progress indicator
                progress_display = gr.Textbox(
                    label="Progress",
                    value="Step 1 of 5: Danger Signs",
                    interactive=False,
                )

                # Step description
                step_description = gr.Markdown(
                    value=_STATE_DESCRIPTIONS[IMCIState.DANGER_SIGNS],
                )

                # Active input group indicator (hidden, used for logic)
                active_group = gr.Textbox(
                    value="danger_signs", visible=False,
                )

                # Status/feedback display
                status_display = gr.Markdown(value="", label="Status")

                gr.Markdown("---")

                # --------------------------------------------------------
                # Input groups — one per IMCI domain
                # --------------------------------------------------------

                # DANGER SIGNS inputs
                with gr.Group(visible=True) as danger_group:
                    gr.Markdown("### Danger Signs Assessment")
                    with gr.Row():
                        danger_image = gr.Image(
                            label="Photo of child (for alertness)",
                            type="filepath",
                            sources=["upload", "webcam"],
                        )
                    danger_text = gr.Textbox(
                        label="Caregiver response",
                        placeholder="Can the child drink? Has the child had convulsions?",
                        lines=2,
                    )
                    danger_btn = gr.Button("Assess Danger Signs", variant="secondary")

                # BREATHING inputs
                with gr.Group(visible=False) as breathing_group:
                    gr.Markdown("### Breathing Assessment")
                    with gr.Row():
                        breathing_video = gr.Video(
                            label="15-second chest video (breathing rate)",
                            sources=["upload", "webcam"],
                        )
                        breathing_image = gr.Image(
                            label="Chest image (indrawing)",
                            type="filepath",
                            sources=["upload", "webcam"],
                        )
                    breathing_audio = gr.Audio(
                        label="Breath sounds recording",
                        type="filepath",
                        sources=["upload", "microphone"],
                    )
                    breathing_cough = gr.Checkbox(
                        label="Child has cough",
                        value=False,
                    )
                    breathing_btn = gr.Button("Assess Breathing", variant="secondary")

                # DIARRHEA inputs
                with gr.Group(visible=False) as diarrhea_group:
                    gr.Markdown("### Diarrhea / Dehydration Assessment")
                    with gr.Row():
                        diarrhea_image = gr.Image(
                            label="Image for dehydration signs (skin pinch, eyes)",
                            type="filepath",
                            sources=["upload", "webcam"],
                        )
                    with gr.Row():
                        diarrhea_check = gr.Checkbox(label="Child has diarrhea", value=False)
                        diarrhea_days = gr.Number(
                            label="Duration (days)", value=0, minimum=0, maximum=60,
                        )
                        diarrhea_blood = gr.Checkbox(label="Blood in stool", value=False)
                    diarrhea_text = gr.Textbox(
                        label="Caregiver response",
                        placeholder="How long has the diarrhea lasted? Any blood?",
                        lines=2,
                    )
                    diarrhea_btn = gr.Button("Assess Diarrhea", variant="secondary")

                # FEVER inputs
                with gr.Group(visible=False) as fever_group:
                    gr.Markdown("### Fever Assessment")
                    with gr.Row():
                        fever_check = gr.Checkbox(label="Child has fever", value=False)
                        fever_days = gr.Number(
                            label="Duration (days)", value=0, minimum=0, maximum=30,
                        )
                    with gr.Row():
                        fever_stiff_neck = gr.Checkbox(label="Stiff neck", value=False)
                        fever_malaria = gr.Checkbox(label="In malaria risk area", value=False)
                    with gr.Row():
                        fever_measles = gr.Checkbox(label="Recent measles", value=False)
                        fever_measles_comp = gr.Checkbox(
                            label="Measles complications", value=False,
                        )
                    fever_btn = gr.Button("Assess Fever", variant="secondary")

                # NUTRITION inputs
                with gr.Group(visible=False) as nutrition_group:
                    gr.Markdown("### Nutrition Assessment")
                    with gr.Row():
                        nutrition_image = gr.Image(
                            label="Photo of child (wasting assessment)",
                            type="filepath",
                            sources=["upload", "webcam"],
                        )
                    nutrition_muac = gr.Number(
                        label="MUAC measurement (mm, 0 = not measured)",
                        value=0, minimum=0, maximum=250,
                    )
                    nutrition_btn = gr.Button("Assess Nutrition", variant="secondary")

                # HEART inputs
                with gr.Group(visible=False) as heart_group:
                    gr.Markdown("### Heart Assessment (Optional)")
                    heart_audio = gr.Audio(
                        label="Heart sounds recording",
                        type="filepath",
                        sources=["upload", "microphone"],
                    )
                    heart_btn = gr.Button("Assess Heart", variant="secondary")

                gr.Markdown("---")

                # Finding display
                finding_display = gr.Markdown(
                    value="*Assessment results will appear here after each step.*",
                    label="Step Result",
                )

                # Next step / finish controls
                with gr.Row():
                    next_btn = gr.Button(
                        "Next Step >>",
                        variant="primary",
                        size="lg",
                    )

                # TTS playback
                with gr.Row():
                    tts_audio = gr.Audio(
                        label="Treatment audio (TTS)",
                        type="filepath",
                        visible=True,
                        interactive=False,
                    )

            # ============================================================
            # TAB 2: Results
            # ============================================================

            with gr.Tab("Results"):
                refresh_results_btn = gr.Button(
                    "Refresh Results",
                    variant="primary",
                )
                results_display = gr.Markdown(
                    value="*Run an assessment first, then view results here.*",
                )

        # ------------------------------------------------------------------
        # Wire up event handlers
        # ------------------------------------------------------------------

        # Model loading
        load_model_btn.click(
            fn=on_load_model,
            inputs=[],
            outputs=[model_status, progress_display],
        )

        # Start assessment
        start_btn.click(
            fn=on_start_assessment,
            inputs=[age_input, language_input],
            outputs=[status_display, step_description, progress_display, active_group],
        )

        # Domain assessment buttons
        danger_btn.click(
            fn=on_assess_danger_signs,
            inputs=[danger_image, danger_text],
            outputs=[finding_display, status_display],
        )

        breathing_btn.click(
            fn=on_assess_breathing,
            inputs=[breathing_video, breathing_image, breathing_audio, breathing_cough],
            outputs=[finding_display, status_display],
        )

        diarrhea_btn.click(
            fn=on_assess_diarrhea,
            inputs=[
                diarrhea_image, diarrhea_check, diarrhea_days,
                diarrhea_blood, diarrhea_text,
            ],
            outputs=[finding_display, status_display],
        )

        fever_btn.click(
            fn=on_assess_fever,
            inputs=[
                fever_check, fever_days, fever_stiff_neck,
                fever_malaria, fever_measles, fever_measles_comp,
            ],
            outputs=[finding_display, status_display],
        )

        nutrition_btn.click(
            fn=on_assess_nutrition,
            inputs=[nutrition_image, nutrition_muac],
            outputs=[finding_display, status_display],
        )

        heart_btn.click(
            fn=on_assess_heart,
            inputs=[heart_audio],
            outputs=[finding_display, status_display],
        )

        # Next step — advance and toggle input group visibility
        def _advance_and_update() -> tuple[
            str, str, str, str,
            Any, Any, Any, Any, Any, Any,
            str,
        ]:
            msg, desc, progress, visibility = on_next_step()

            finding_text = (
                "*Assessment complete. Switch to the Results tab.*"
                if visibility == "none"
                else "*Click the assess button above, then advance.*"
            )

            return (
                msg,                                                     # status_display
                desc,                                                    # step_description
                progress,                                                # progress_display
                visibility,                                              # active_group
                gr.Group(visible=(visibility == "danger_signs")),         # danger_group
                gr.Group(visible=(visibility == "breathing")),            # breathing_group
                gr.Group(visible=(visibility == "diarrhea")),             # diarrhea_group
                gr.Group(visible=(visibility == "fever")),                # fever_group
                gr.Group(visible=(visibility == "nutrition")),            # nutrition_group
                gr.Group(visible=(visibility == "heart")),                # heart_group
                finding_text,                                            # finding_display
            )

        next_btn.click(
            fn=_advance_and_update,
            inputs=[],
            outputs=[
                status_display, step_description, progress_display, active_group,
                danger_group, breathing_group, diarrhea_group,
                fever_group, nutrition_group, heart_group,
                finding_display,
            ],
        )

        # Results tab
        refresh_results_btn.click(
            fn=on_view_results,
            inputs=[],
            outputs=[results_display],
        )

    return app


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Launch the Malaika Gradio app."""
    config = load_config()

    logger.info("malaika_app_starting", features=str(config.features))

    app = create_app(config)
    app.launch(
        share=True,
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
    )


if __name__ == "__main__":
    main()
