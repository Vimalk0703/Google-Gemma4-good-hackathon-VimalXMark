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

# ---------------------------------------------------------------------------
# Sample data paths
# ---------------------------------------------------------------------------

_SAMPLES_DIR = Path(__file__).parent.parent / "data" / "samples"
_SAMPLE_CHILD = str(_SAMPLES_DIR / "sample_child.jpg")
_SAMPLE_CHEST = str(_SAMPLES_DIR / "sample_chest.jpg")
_SAMPLE_FACE = str(_SAMPLES_DIR / "sample_face.jpg")
_SAMPLE_SPECTROGRAM = str(_SAMPLES_DIR / "sample_spectrogram.png")

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BANNER = (
    "**Malaika** (Angel in Swahili) -- WHO IMCI Child Survival AI powered by Gemma 4\n\n"
    "Demo for Gemma 4 Good Hackathon -- **not for clinical use**"
)

# Language display names -> internal codes
_LANGUAGE_MAP: dict[str, str] = {
    "English": "en",
    "Swahili": "sw",
    "Hindi": "hi",
    "French": "fr",
}
_LANGUAGE_NAMES: list[str] = list(_LANGUAGE_MAP.keys())

# Ordered list of user-facing assessment steps (used for progress bar)
_ASSESSMENT_STEPS: list[IMCIState] = [
    IMCIState.DANGER_SIGNS,
    IMCIState.BREATHING,
    IMCIState.DIARRHEA,
    IMCIState.FEVER,
    IMCIState.NUTRITION,
]

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

# User-friendly guidance per step
_STEP_GUIDANCE: dict[IMCIState, str] = {
    IMCIState.DANGER_SIGNS: (
        "Upload a photo of the child and answer questions about their alertness. "
        "This helps identify any urgent danger signs requiring immediate action."
    ),
    IMCIState.BREATHING: (
        "Record a short chest video, take a chest photo, or record breathing sounds. "
        "Malaika will check for fast breathing, chest indrawing, and abnormal sounds."
    ),
    IMCIState.DIARRHEA: (
        "Answer questions about diarrhea symptoms and upload a photo to check for "
        "dehydration signs like sunken eyes or slow skin pinch."
    ),
    IMCIState.FEVER: (
        "Answer questions about fever, its duration, and any related symptoms like "
        "stiff neck or recent measles exposure."
    ),
    IMCIState.NUTRITION: (
        "Upload a photo to assess for visible wasting. Enter the MUAC measurement "
        "if available. This checks for malnutrition."
    ),
    IMCIState.HEART_MEMS: (
        "Optional: Record heart sounds using a phone microphone or digital stethoscope "
        "for heart rate assessment."
    ),
    IMCIState.CLASSIFY: "Malaika is classifying findings using WHO IMCI protocol...",
    IMCIState.TREAT: "Generating treatment plan...",
    IMCIState.COMPLETE: "Assessment complete. Switch to the Results tab to view the full report.",
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
        """Progress indicator text (plain)."""
        state = self.current_state
        label = _STATE_LABELS.get(state, state.name)
        if state in (IMCIState.CLASSIFY, IMCIState.TREAT, IMCIState.COMPLETE):
            return f"Step {self.total_steps} of {self.total_steps}: {label}"
        return f"Step {self.step_number} of {self.total_steps}: {label}"

    def progress_html(self) -> str:
        """Build an HTML progress bar with step indicators."""
        state = self.current_state
        total = self.total_steps
        if state in (IMCIState.CLASSIFY, IMCIState.TREAT, IMCIState.COMPLETE):
            current = total
        else:
            current = self.step_number

        pct = int((current / total) * 100)

        # Build step dots
        dots: list[str] = []
        for i, st in enumerate(_ASSESSMENT_STEPS[:total]):
            idx = i + 1
            lbl = _STATE_LABELS.get(st, st.name)
            if idx < current:
                cls = "step-dot step-done"
            elif idx == current:
                cls = "step-dot step-active"
            else:
                cls = "step-dot step-pending"
            dots.append(
                f'<div class="{cls}" title="{lbl}">'
                f'<span class="step-num">{idx}</span>'
                f'<span class="step-label">{lbl}</span>'
                f'</div>'
            )

        dots_html = "".join(dots)
        label = _STATE_LABELS.get(state, state.name)

        return (
            f'<div class="progress-container">'
            f'<div class="progress-bar-track">'
            f'<div class="progress-bar-fill" style="width:{pct}%"></div>'
            f'</div>'
            f'<div class="step-dots">{dots_html}</div>'
            f'<div class="progress-label">Step {current} of {total}: {label}</div>'
            f'</div>'
        )

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
                "Please wait for model to finish loading."
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
    bg_light = {
        Severity.GREEN: "#d4edda",
        Severity.YELLOW: "#fff3cd",
        Severity.RED: "#f8d7da",
    }
    text_color = {
        Severity.GREEN: "#155724",
        Severity.YELLOW: "#856404",
        Severity.RED: "#721c24",
    }
    return (
        f'<div style="display:inline-block;background:{bg_light[severity]};'
        f'border:2px solid {color};border-radius:8px;padding:10px 24px;'
        f'text-align:center;margin:8px 0;">'
        f'<span style="color:{text_color[severity]};font-weight:bold;'
        f'font-size:1.3em;letter-spacing:1px;">{label}</span>'
        f'</div>'
    )


def _finding_to_markdown(finding: ClinicalFinding) -> str:
    """Convert a ClinicalFinding to a styled card-like markdown block."""
    state_label = _STATE_LABELS.get(finding.imci_state, finding.imci_state.name)
    status = finding.finding_status.value.replace("_", " ").title()
    classifications = ", ".join(
        c.value.replace("_", " ").title() for c in finding.classifications
    )

    lines: list[str] = []
    lines.append(f"### {state_label}")
    lines.append("")
    lines.append(f"| Field | Value |")
    lines.append(f"|-------|-------|")
    lines.append(f"| **Status** | {status} |")
    if classifications:
        lines.append(f"| **Classifications** | {classifications} |")
    if finding.notes:
        lines.append(f"| **Notes** | {finding.notes} |")

    # Confidence from perception results
    for pr in finding.perception_results:
        lines.append(f"| **Confidence** | {pr.confidence:.0%} |")
        if pr.description:
            lines.append(f"| **Observation** | {pr.description} |")

    return "\n".join(lines)


def _build_results_markdown(app_state: AppState) -> str:
    """Build full results markdown from the completed assessment."""
    if app_state.engine is None:
        return "*No assessment has been run yet. Complete an assessment on the Assessment tab first.*"

    result = app_state.engine.get_result()

    lines: list[str] = []
    lines.append("# Assessment Results\n")

    # Severity banner
    lines.append(f"## Overall Severity\n\n{_severity_badge(result.severity)}\n")

    # Referral urgency
    referral_text = {
        "none": "No referral needed -- home care",
        "24h": "See a health worker within 24 hours",
        "immediate": "URGENT: Transport to health facility immediately",
    }
    referral_color = {
        "none": "#155724",
        "24h": "#856404",
        "immediate": "#721c24",
    }
    urgency_val = result.referral_urgency.value
    r_color = referral_color.get(urgency_val, "#333")
    r_text = referral_text.get(urgency_val, urgency_val)
    lines.append(
        f'<div style="padding:8px 16px;border-left:4px solid {r_color};'
        f'background:#f8f9fa;margin:8px 0;font-weight:600;color:{r_color};">'
        f'{r_text}</div>\n'
    )

    # Classifications
    lines.append("## Classifications\n")
    if result.classifications:
        for ct in result.classifications:
            label = ct.value.replace("_", " ").title()
            lines.append(f"- {label}")
    else:
        lines.append("- No classifications assigned")
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
        lines.append(
            '<div style="background:#e8f4fd;border:1px solid #bee5eb;'
            'border-radius:8px;padding:16px;margin:8px 0;">\n'
        )
        lines.append(result.treatment_text)
        lines.append("\n</div>")
        lines.append("")

    # Export note
    lines.append("---")
    lines.append(
        "*To save this report, use your browser Print function (Ctrl+P / Cmd+P) "
        "to export as PDF.*"
    )
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
        return status, app_state.progress_html()

    def on_start_assessment(
        age_months: int, language: str,
    ) -> tuple[str, str, str, str]:
        """Start a new assessment."""
        age = max(2, min(59, int(age_months)))
        lang_code = _LANGUAGE_MAP.get(language, language)
        msg = app_state.start_assessment(age, lang_code)
        state = app_state.current_state
        desc = _STATE_DESCRIPTIONS.get(state, "")
        guidance = _STEP_GUIDANCE.get(state, desc)
        guidance_html = f'<div class="step-guidance">{guidance}</div>'
        progress = app_state.progress_html()
        return msg, guidance_html, progress, _get_input_visibility(state)

    def _check_engine(expected_state: IMCIState) -> str | None:
        """Check engine is ready and on the expected state. Returns error or None."""
        if app_state.engine is None:
            return "No assessment in progress. Click 'Start New Assessment' first."
        if app_state.current_state != expected_state:
            return f"Not on {_STATE_LABELS.get(expected_state, expected_state.name)} step (current: {app_state.current_state.name})."
        return None

    def on_assess_danger_signs(
        image: str | None,
        caregiver_text: str,
    ) -> tuple[str, str]:
        """Run danger signs assessment."""
        err = _check_engine(IMCIState.DANGER_SIGNS)
        if err:
            return err, ""
        try:
            finding = app_state.engine.assess_danger_signs(
                image_path=Path(image) if image else None,
                caregiver_response=caregiver_text or None,
            )
            return _finding_to_markdown(finding), ""
        except Exception as exc:
            logger.error("assess_danger_signs_failed", error=str(exc))
            return f"Assessment error: {exc}", ""

    def on_assess_breathing(
        video: str | None,
        image: str | None,
        spectrogram: str | None,
        audio: str | None,
        has_cough: bool,
    ) -> tuple[str, str]:
        """Run breathing assessment with spectrogram support."""
        err = _check_engine(IMCIState.BREATHING)
        if err:
            return err, ""
        try:
            finding = app_state.engine.assess_breathing(
                video_path=Path(video) if video else None,
                image_path=Path(image) if image else None,
                spectrogram_path=Path(spectrogram) if spectrogram else None,
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
        err = _check_engine(IMCIState.DIARRHEA)
        if err:
            return err, ""
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
        err = _check_engine(IMCIState.FEVER)
        if err:
            return err, ""
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
        err = _check_engine(IMCIState.NUTRITION)
        if err:
            return err, ""
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
        err = _check_engine(IMCIState.HEART_MEMS)
        if err:
            return err, ""
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
        guidance = _STEP_GUIDANCE.get(state, desc)
        progress = app_state.progress_html()
        visibility = _get_input_visibility(state)
        return msg, guidance, progress, visibility

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

    _custom_css = """
        /* -- Global -- */
        .gradio-container {
            max-width: 960px !important;
            margin: 0 auto !important;
            font-family: 'Inter', 'Segoe UI', system-ui, sans-serif !important;
        }

        /* -- Header branding -- */
        .malaika-header {
            text-align: center;
            padding: 24px 16px 16px;
            background: linear-gradient(135deg, #e8f4fd 0%, #f0f7ff 100%);
            border-bottom: 3px solid #2979b9;
            border-radius: 12px 12px 0 0;
            margin-bottom: 8px;
        }
        .malaika-header h1 {
            margin: 0 0 4px;
            font-size: 2em;
            color: #1a5276;
            letter-spacing: 1px;
        }
        .malaika-header .tagline {
            color: #2e86c1;
            font-size: 1.05em;
            margin: 0;
        }
        .malaika-header .disclaimer {
            color: #7f8c8d;
            font-size: 0.85em;
            margin-top: 6px;
        }

        /* -- Demo mode banner -- */
        .demo-banner {
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 8px;
            padding: 12px 20px;
            margin: 8px 0 12px;
            text-align: center;
            color: #856404;
            font-weight: 600;
        }
        .demo-banner .demo-title {
            font-size: 1.15em;
            margin-bottom: 4px;
        }
        .demo-banner .demo-desc {
            font-weight: 400;
            font-size: 0.9em;
        }

        /* -- Progress bar -- */
        .progress-container {
            margin: 12px 0;
        }
        .progress-bar-track {
            width: 100%;
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 10px;
        }
        .progress-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, #2979b9, #21a0e8);
            border-radius: 4px;
            transition: width 0.4s ease;
        }
        .step-dots {
            display: flex;
            justify-content: space-between;
            gap: 4px;
            margin-bottom: 6px;
        }
        .step-dot {
            flex: 1;
            text-align: center;
            padding: 6px 2px;
            border-radius: 6px;
            font-size: 0.78em;
            line-height: 1.3;
        }
        .step-dot .step-num {
            display: block;
            font-weight: 700;
            font-size: 1.1em;
        }
        .step-dot .step-label {
            display: block;
            font-size: 0.85em;
        }
        .step-done {
            background: #d4edda;
            color: #155724;
            border: 1px solid #a3d9a5;
        }
        .step-active {
            background: #cce5ff;
            color: #004085;
            border: 2px solid #2979b9;
            font-weight: 700;
        }
        .step-pending {
            background: #f8f9fa;
            color: #6c757d;
            border: 1px solid #dee2e6;
        }
        .progress-label {
            text-align: center;
            font-weight: 600;
            color: #2c3e50;
            font-size: 0.95em;
        }

        /* -- Step guidance -- */
        .step-guidance {
            background: #f0f7ff;
            border-left: 4px solid #2979b9;
            border-radius: 0 8px 8px 0;
            padding: 12px 16px;
            margin: 8px 0;
            color: #2c3e50;
            font-size: 0.95em;
        }

        /* -- Finding card -- */
        .finding-card {
            background: #ffffff;
            border: 1px solid #dee2e6;
            border-radius: 10px;
            padding: 16px;
            margin: 8px 0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }

        /* -- Assessment group styling -- */
        .assess-group {
            background: #fafbfc;
            border: 1px solid #e1e4e8;
            border-radius: 10px;
            padding: 16px !important;
            margin: 8px 0;
        }
        .assess-group h3 {
            color: #1a5276;
            border-bottom: 2px solid #e8f4fd;
            padding-bottom: 6px;
            margin-top: 0;
        }

        /* -- Buttons -- */
        .next-step-btn {
            min-height: 52px !important;
            font-size: 1.15em !important;
            font-weight: 700 !important;
            letter-spacing: 0.5px;
        }
        .load-model-btn {
            min-height: 56px !important;
            font-size: 1.2em !important;
            font-weight: 700 !important;
        }
        .assess-btn {
            margin-top: 8px !important;
        }

        /* -- Results tab -- */
        .results-area {
            background: #ffffff;
            border: 1px solid #dee2e6;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }

        /* -- Footer -- */
        .malaika-footer {
            text-align: center;
            padding: 16px;
            margin-top: 12px;
            border-top: 2px solid #e8f4fd;
            color: #7f8c8d;
            font-size: 0.85em;
        }
        .malaika-footer a { color: #2979b9; text-decoration: none; }

        /* -- Mobile responsive -- */
        @media (max-width: 768px) {
            .gradio-container { padding: 0 4px !important; }
            .malaika-header h1 { font-size: 1.5em; }
            .step-dot .step-label { display: none; }
            .step-dot .step-num { font-size: 1em; }
            .step-dots { gap: 2px; }

            /* Stack inputs vertically */
            .gr-row { flex-direction: column !important; }

            /* Larger touch targets */
            button, .gr-button {
                min-height: 48px !important;
                font-size: 1em !important;
            }
            input, select, textarea {
                min-height: 44px !important;
                font-size: 16px !important;  /* Prevents iOS zoom */
            }
            .gr-check-radio { min-height: 44px !important; }
        }

        @media (max-width: 480px) {
            .malaika-header { padding: 16px 8px 12px; }
            .malaika-header h1 { font-size: 1.3em; }
            .malaika-header .tagline { font-size: 0.9em; }
            .step-dot { padding: 4px 1px; font-size: 0.7em; }
        }
    """

    with gr.Blocks(
        title="Malaika -- WHO IMCI Child Health AI",
        theme=gr.themes.Soft(
            primary_hue=gr.themes.colors.blue,
            secondary_hue=gr.themes.colors.cyan,
            neutral_hue=gr.themes.colors.slate,
        ),
        css=_custom_css,
    ) as app:

        # Header branding
        gr.HTML(
            '<div class="malaika-header">'
            '<h1>Malaika</h1>'
            '<p class="tagline">Angel in Swahili -- '
            'WHO IMCI Child Survival AI powered by Gemma 4</p>'
            '<p class="disclaimer">Hackathon demo -- not for clinical use</p>'
            '</div>'
        )

        with gr.Tabs():

            # ============================================================
            # TAB 1: Assessment
            # ============================================================

            with gr.Tab("Assessment"):

                # Model status bar
                model_status = gr.Textbox(
                    label="Model Status",
                    value="Loading Gemma 4 model...",
                    interactive=False,
                    lines=1,
                )

                gr.HTML('<hr style="border:none;border-top:2px solid #e8f4fd;margin:16px 0;">')

                # Assessment setup
                with gr.Row():
                    with gr.Column(scale=2):
                        age_input = gr.Slider(
                            minimum=2, maximum=59, value=12, step=1,
                            label="Child's Age (months)",
                            info="WHO IMCI covers ages 2 to 59 months",
                        )
                    with gr.Column(scale=1):
                        language_input = gr.Dropdown(
                            choices=_LANGUAGE_NAMES,
                            value="English",
                            label="Language",
                            info="Language for treatment instructions",
                        )
                    with gr.Column(scale=1, min_width=180):
                        start_btn = gr.Button(
                            "Start New Assessment",
                            variant="primary",
                            size="lg",
                        )

                # Progress indicator (HTML for styled progress bar)
                progress_display = gr.HTML(
                    value=app_state.progress_html(),
                )

                # Step guidance
                step_description = gr.HTML(
                    value=(
                        '<div class="step-guidance">'
                        + _STEP_GUIDANCE[IMCIState.DANGER_SIGNS]
                        + '</div>'
                    ),
                )

                # Active input group indicator (hidden, used for logic)
                active_group = gr.Textbox(
                    value="danger_signs", visible=False,
                )

                # Status/feedback display
                status_display = gr.Markdown(value="", label="Status")

                # --------------------------------------------------------
                # Input groups — one per IMCI domain
                # --------------------------------------------------------

                # DANGER SIGNS inputs
                with gr.Group(
                    visible=True, elem_classes=["assess-group"],
                ) as danger_group:
                    gr.Markdown("### Danger Signs Assessment")
                    with gr.Row():
                        danger_image = gr.Image(
                            label="Photo of child (for alertness)",
                            type="filepath",
                            sources=["upload", "webcam"],
                            value=_SAMPLE_CHILD if Path(_SAMPLE_CHILD).exists() else None,
                        )
                    danger_text = gr.Textbox(
                        label="Caregiver response",
                        value="The child is alert but has a fever. Can drink but is irritable.",
                        lines=2,
                    )
                    danger_btn = gr.Button(
                        "Assess Danger Signs",
                        variant="secondary",
                        elem_classes=["assess-btn"],
                    )

                # BREATHING inputs
                with gr.Group(
                    visible=False, elem_classes=["assess-group"],
                ) as breathing_group:
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
                            value=_SAMPLE_CHEST if Path(_SAMPLE_CHEST).exists() else None,
                        )
                    with gr.Row():
                        breathing_spectrogram = gr.Image(
                            label="Breath sound spectrogram",
                            type="filepath",
                            sources=["upload"],
                            value=_SAMPLE_SPECTROGRAM if Path(_SAMPLE_SPECTROGRAM).exists() else None,
                        )
                    breathing_audio = gr.Audio(
                        label="Breath sounds recording",
                        type="filepath",
                        sources=["upload", "microphone"],
                    )
                    breathing_cough = gr.Checkbox(
                        label="Child has cough",
                        value=True,
                    )
                    breathing_btn = gr.Button(
                        "Assess Breathing",
                        variant="secondary",
                        elem_classes=["assess-btn"],
                    )

                # DIARRHEA inputs
                with gr.Group(
                    visible=False, elem_classes=["assess-group"],
                ) as diarrhea_group:
                    gr.Markdown("### Diarrhea / Dehydration Assessment")
                    with gr.Row():
                        diarrhea_image = gr.Image(
                            label="Image for dehydration signs (skin pinch, eyes)",
                            type="filepath",
                            sources=["upload", "webcam"],
                            value=_SAMPLE_FACE if Path(_SAMPLE_FACE).exists() else None,
                        )
                    with gr.Row():
                        diarrhea_check = gr.Checkbox(
                            label="Child has diarrhea", value=True,
                        )
                        diarrhea_days = gr.Number(
                            label="Duration (days)",
                            value=3, minimum=0, maximum=60,
                        )
                        diarrhea_blood = gr.Checkbox(
                            label="Blood in stool", value=False,
                        )
                    diarrhea_text = gr.Textbox(
                        label="Caregiver response",
                        value="Diarrhea for 3 days, watery stools, child is thirsty and drinks eagerly.",
                        lines=2,
                    )
                    diarrhea_btn = gr.Button(
                        "Assess Diarrhea",
                        variant="secondary",
                        elem_classes=["assess-btn"],
                    )

                # FEVER inputs
                with gr.Group(
                    visible=False, elem_classes=["assess-group"],
                ) as fever_group:
                    gr.Markdown("### Fever Assessment")
                    with gr.Row():
                        fever_check = gr.Checkbox(
                            label="Child has fever", value=True,
                        )
                        fever_days = gr.Number(
                            label="Duration (days)",
                            value=2, minimum=0, maximum=30,
                        )
                    with gr.Row():
                        fever_stiff_neck = gr.Checkbox(
                            label="Stiff neck", value=False,
                        )
                        fever_malaria = gr.Checkbox(
                            label="In malaria risk area", value=True,
                        )
                    with gr.Row():
                        fever_measles = gr.Checkbox(
                            label="Recent measles", value=False,
                        )
                        fever_measles_comp = gr.Checkbox(
                            label="Measles complications", value=False,
                        )
                    fever_btn = gr.Button(
                        "Assess Fever",
                        variant="secondary",
                        elem_classes=["assess-btn"],
                    )

                # NUTRITION inputs
                with gr.Group(
                    visible=False, elem_classes=["assess-group"],
                ) as nutrition_group:
                    gr.Markdown("### Nutrition Assessment")
                    with gr.Row():
                        nutrition_image = gr.Image(
                            label="Photo of child (wasting assessment)",
                            type="filepath",
                            sources=["upload", "webcam"],
                            value=_SAMPLE_CHILD if Path(_SAMPLE_CHILD).exists() else None,
                        )
                    nutrition_muac = gr.Number(
                        label="MUAC measurement (mm, 0 = not measured)",
                        value=125, minimum=0, maximum=250,
                    )
                    nutrition_btn = gr.Button(
                        "Assess Nutrition",
                        variant="secondary",
                        elem_classes=["assess-btn"],
                    )

                # HEART inputs
                with gr.Group(
                    visible=False, elem_classes=["assess-group"],
                ) as heart_group:
                    gr.Markdown("### Heart Assessment (Optional)")
                    heart_audio = gr.Audio(
                        label="Heart sounds recording",
                        type="filepath",
                        sources=["upload", "microphone"],
                    )
                    heart_btn = gr.Button(
                        "Assess Heart",
                        variant="secondary",
                        elem_classes=["assess-btn"],
                    )

                gr.HTML(
                    '<hr style="border:none;border-top:2px solid #e8f4fd;'
                    'margin:16px 0;">'
                )

                # Finding display (card-like)
                finding_display = gr.Markdown(
                    value=(
                        "*Assessment results will appear here after each step.*"
                    ),
                    label="Step Result",
                    elem_classes=["finding-card"],
                )

                # Next step / finish controls
                with gr.Row():
                    next_btn = gr.Button(
                        "Next Step  >>",
                        variant="primary",
                        size="lg",
                        elem_classes=["next-step-btn"],
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
                gr.HTML(
                    '<div style="text-align:center;margin:12px 0 8px;">'
                    '<p style="color:#2c3e50;font-size:1.05em;">'
                    'Complete an assessment to see the full clinical summary '
                    'and treatment plan below.</p>'
                    '</div>'
                )
                refresh_results_btn = gr.Button(
                    "Refresh Results",
                    variant="primary",
                    size="lg",
                )
                results_display = gr.Markdown(
                    value=(
                        "*Run an assessment first, then view results here.*"
                    ),
                    elem_classes=["results-area"],
                )

        # Footer
        gr.HTML(
            '<div class="malaika-footer">'
            'Malaika -- WHO IMCI Child Survival AI | '
            'Google Gemma 4 Good Hackathon 2026 | '
            'Powered by '
            '<a href="https://ai.google.dev/gemma" target="_blank">Gemma 4</a>'
            ' | Not for clinical use'
            '</div>'
        )

        # ------------------------------------------------------------------
        # Wire up event handlers
        # ------------------------------------------------------------------

        # Auto-load model on app startup
        app.load(
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
            inputs=[breathing_video, breathing_image, breathing_spectrogram, breathing_audio, breathing_cough],
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
            msg, guidance, progress, visibility = on_next_step()

            guidance_html = f'<div class="step-guidance">{guidance}</div>'

            finding_text = (
                "*Assessment complete. Switch to the Results tab.*"
                if visibility == "none"
                else "*Click the assess button above, then advance.*"
            )

            return (
                msg,                                                     # status_display
                guidance_html,                                           # step_description
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
