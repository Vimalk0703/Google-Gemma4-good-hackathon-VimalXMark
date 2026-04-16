"""Malaika Conversational UI — chat-based IMCI assessment.

Gemma 4 guides the caregiver through WHO IMCI protocol steps
conversationally. The caregiver uploads photos, answers questions,
and receives a classification + treatment plan.

Run with: python -m malaika.chat_app
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog

from malaika.config import MalaikaConfig, load_config
from malaika.types import (
    ClassificationType,
    FindingStatus,
    IMCIState,
    Severity,
)

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# IMCI Chat Steps
# ---------------------------------------------------------------------------

STEPS = [
    "welcome",
    "age",
    "danger_signs_photo",
    "danger_signs_questions",
    "breathing_photo",
    "breathing_questions",
    "diarrhea_photo",
    "diarrhea_questions",
    "fever_questions",
    "nutrition_photo",
    "classify",
    "complete",
]


# ---------------------------------------------------------------------------
# Chat Session State
# ---------------------------------------------------------------------------

class ChatSession:
    """Manages one IMCI assessment conversation."""

    def __init__(self, config: MalaikaConfig) -> None:
        self.config = config
        self.inference: Any = None
        self.model_loaded = False
        self.step = "welcome"
        self.age_months: int = 12
        self.language: str = "en"

        # Clinical findings collected during conversation
        self.findings: dict[str, Any] = {
            "lethargic": False,
            "unconscious": False,
            "unable_to_drink": False,
            "vomits_everything": False,
            "has_convulsions": False,
            "breathing_rate": None,
            "has_indrawing": False,
            "has_stridor": False,
            "has_wheeze": False,
            "has_cough": False,
            "has_diarrhea": False,
            "diarrhea_days": 0,
            "blood_in_stool": False,
            "sunken_eyes": False,
            "skin_pinch_slow": False,
            "has_fever": False,
            "fever_days": 0,
            "stiff_neck": False,
            "malaria_risk": False,
            "visible_wasting": False,
            "edema": False,
            "muac_mm": None,
        }

        # Image analysis results from Gemma
        self.image_observations: dict[str, str] = {}

    def advance(self) -> None:
        """Move to the next step."""
        idx = STEPS.index(self.step)
        if idx < len(STEPS) - 1:
            self.step = STEPS[idx + 1]

    def load_model(self) -> str:
        """Load Gemma 4 model."""
        try:
            from malaika.inference import MalaikaInference
            self.inference = MalaikaInference(self.config)
            self.inference.load_model()
            self.model_loaded = True
            return f"Model loaded on {self.inference.device}"
        except Exception as e:
            logger.error("model_load_failed", error=str(e))
            return f"Model load failed: {e}"

    def analyze_image(self, image_path: str, prompt_name: str) -> dict:
        """Run Gemma 4 vision analysis on an image."""
        if not self.model_loaded or self.inference is None:
            return {"error": "Model not loaded"}

        try:
            from malaika.prompts import PromptRegistry
            prompt = PromptRegistry.get(prompt_name)
            raw, validated, retries = self.inference.analyze_image(
                Path(image_path), prompt,
            )
            return validated.parsed
        except Exception as e:
            logger.error("image_analysis_failed", error=str(e), prompt=prompt_name)
            return {"error": str(e)}

    def analyze_with_gemma(self, user_message: str, system_context: str) -> str:
        """Get a conversational response from Gemma 4."""
        if not self.model_loaded or self.inference is None:
            return ""

        try:
            messages = [
                {"role": "system", "content": system_context},
                {"role": "user", "content": user_message},
            ]
            return self.inference.generate(messages, max_tokens=300, temperature=0.3)
        except Exception as e:
            logger.error("gemma_response_failed", error=str(e))
            return ""

    def classify(self) -> dict[str, Any]:
        """Run WHO IMCI classification on collected findings."""
        from malaika.imci_protocol import (
            classify_breathing,
            classify_danger_signs,
            classify_diarrhea,
            classify_fever,
            classify_nutrition,
        )

        results = []

        # Danger signs
        ds = classify_danger_signs(
            lethargic=self.findings["lethargic"],
            unconscious=self.findings["unconscious"],
            unable_to_drink=self.findings["unable_to_drink"],
            vomits_everything=self.findings["vomits_everything"],
        )
        if ds:
            results.append(("Danger Signs", ds.classification, ds.severity))

        # Breathing
        br = classify_breathing(
            age_months=self.age_months,
            has_cough=self.findings["has_cough"],
            breathing_rate=self.findings["breathing_rate"],
            has_indrawing=self.findings["has_indrawing"],
            has_stridor=self.findings["has_stridor"],
            has_wheeze=self.findings["has_wheeze"],
        )
        results.append(("Breathing", br.classification, br.severity))

        # Diarrhea
        if self.findings["has_diarrhea"]:
            dd = classify_diarrhea(
                has_diarrhea=True,
                duration_days=self.findings["diarrhea_days"],
                blood_in_stool=self.findings["blood_in_stool"],
                sunken_eyes=self.findings["sunken_eyes"],
                skin_pinch_slow=self.findings["skin_pinch_slow"],
            )
            if dd:
                results.append(("Diarrhea", dd.classification, dd.severity))

        # Fever
        if self.findings["has_fever"]:
            fv = classify_fever(
                has_fever=True,
                duration_days=self.findings["fever_days"],
                stiff_neck=self.findings["stiff_neck"],
                malaria_risk=self.findings["malaria_risk"],
            )
            if fv:
                results.append(("Fever", fv.classification, fv.severity))

        # Nutrition
        nt = classify_nutrition(
            visible_wasting=self.findings["visible_wasting"],
            edema=self.findings["edema"],
            muac_mm=self.findings["muac_mm"],
        )
        results.append(("Nutrition", nt.classification, nt.severity))

        # Overall severity
        severities = [s for _, _, s in results]
        if Severity.RED in severities:
            overall = Severity.RED
            urgency = "URGENT: Go to a health facility IMMEDIATELY"
        elif Severity.YELLOW in severities:
            overall = Severity.YELLOW
            urgency = "See a health worker within 24 hours"
        else:
            overall = Severity.GREEN
            urgency = "Treat at home. Follow up in 5 days if not improving."

        return {
            "results": results,
            "overall_severity": overall,
            "urgency": urgency,
        }


# ---------------------------------------------------------------------------
# Conversation Handler
# ---------------------------------------------------------------------------

MALAIKA_SYSTEM = (
    "You are Malaika, a caring and warm child health assistant. "
    "You are guiding a mother through a WHO IMCI child health assessment. "
    "Speak simply, warmly, and clearly. Use short sentences. "
    "You are NOT a doctor — you are a decision support tool. "
    "Always say 'based on what I can see' not 'I diagnose'. "
    "When analyzing images, describe what you observe specifically. "
    "Do NOT use thinking mode. Respond directly."
)


def process_message(
    message: dict | str,
    history: list,
    session: ChatSession,
) -> str:
    """Process a user message and return Malaika's response.

    Args:
        message: User's text message or dict with text + files.
        history: Gradio chat history.
        session: Current ChatSession state.

    Returns:
        Malaika's response text.
    """
    # Extract text and image from message
    if isinstance(message, dict):
        user_text = message.get("text", "").strip()
        files = message.get("files", [])
        image_path = files[0] if files else None
    else:
        user_text = str(message).strip()
        image_path = None

    step = session.step

    # --- WELCOME ---
    if step == "welcome":
        session.advance()  # -> age
        return (
            "Hello, I'm **Malaika** — your child health assistant.\n\n"
            "I'll help you check on your child's health using the WHO IMCI protocol. "
            "I'll guide you step by step.\n\n"
            "**How old is your child in months?** (2 to 59 months)"
        )

    # --- AGE ---
    if step == "age":
        # Try to extract age from text
        age = _extract_number(user_text)
        if age and 2 <= age <= 59:
            session.age_months = age
            session.advance()  # -> danger_signs_photo
            return (
                f"Thank you. Your child is **{age} months** old.\n\n"
                "Let's begin the assessment.\n\n"
                "**Step 1: Danger Signs**\n\n"
                "Please take a photo of your child so I can check their alertness. "
                "Make sure the child's face and eyes are visible.\n\n"
                "*Tap the 📎 button to upload or take a photo.*"
            )
        else:
            return (
                "I need your child's age in months (between 2 and 59). "
                "For example, type **12** if your child is 12 months old."
            )

    # --- DANGER SIGNS: PHOTO ---
    if step == "danger_signs_photo":
        if image_path:
            # Analyze the image with Gemma 4
            result = session.analyze_image(image_path, "danger.assess_alertness")

            if "error" not in result:
                alertness = result.get("alertness", "alert")
                session.findings["lethargic"] = alertness == "lethargic"
                session.findings["unconscious"] = alertness == "unconscious"
                description = result.get("description", "")
                confidence = result.get("confidence", 0)

                session.image_observations["danger_signs"] = description

                if alertness == "alert":
                    obs = f"Your child appears **alert and responsive**. {description}"
                elif alertness == "lethargic":
                    obs = f"**Warning:** Your child appears lethargic (abnormally sleepy). {description}"
                else:
                    obs = f"**URGENT:** Your child appears unconscious. {description}"

                session.advance()  # -> danger_signs_questions
                return (
                    f"I've analyzed the photo.\n\n{obs}\n\n"
                    f"*(Confidence: {confidence:.0%})*\n\n"
                    "Now I need to ask a few questions:\n\n"
                    "**Can your child drink or breastfeed?**"
                )
            else:
                # Gemma failed — ask to try again or skip
                session.advance()  # -> danger_signs_questions
                return (
                    "I couldn't analyze the photo clearly. That's okay — "
                    "let me ask you some questions instead.\n\n"
                    "**Can your child drink or breastfeed?**"
                )
        else:
            return (
                "I need a photo of your child to check for danger signs. "
                "Please upload one using the 📎 button.\n\n"
                "Or type **skip** to continue with questions only."
            )

    # --- DANGER SIGNS: QUESTIONS ---
    if step == "danger_signs_questions":
        lower = user_text.lower()

        # Parse responses about drinking/vomiting/convulsions
        if session.model_loaded:
            context = (
                f"{MALAIKA_SYSTEM}\n\n"
                "The caregiver was asked about their child's ability to drink. "
                "Extract whether the child can drink and if they vomit everything. "
                "Respond with a brief, warm acknowledgment and then ask: "
                "'Has your child had any convulsions or fits?'"
            )
            gemma_response = session.analyze_with_gemma(user_text, context)

        # Simple keyword parsing for findings
        if any(w in lower for w in ["no", "cannot", "can't", "unable", "won't"]):
            session.findings["unable_to_drink"] = True
        if any(w in lower for w in ["vomit", "throw up", "throws up"]):
            session.findings["vomits_everything"] = True

        session.advance()  # -> breathing_photo
        has_danger = (
            session.findings["lethargic"]
            or session.findings["unconscious"]
            or session.findings["unable_to_drink"]
            or session.findings["vomits_everything"]
        )

        if has_danger:
            danger_note = "\n\n**Note:** I've detected some danger signs. We'll continue the full assessment."
        else:
            danger_note = "\n\nNo danger signs detected so far. Good."

        return (
            f"Thank you for that information.{danger_note}\n\n"
            "**Step 2: Breathing Assessment**\n\n"
            "Please take a photo of your child's **chest area**. "
            "I'll check for chest indrawing (when the lower chest pulls inward during breathing).\n\n"
            "*Tap 📎 to upload or take a chest photo.*"
        )

    # --- BREATHING: PHOTO ---
    if step == "breathing_photo":
        if image_path:
            result = session.analyze_image(image_path, "breathing.detect_chest_indrawing")

            if "error" not in result:
                indrawing = result.get("indrawing_detected", False)
                session.findings["has_indrawing"] = indrawing
                description = result.get("description", "")
                confidence = result.get("confidence", 0)

                if indrawing:
                    obs = f"**Warning:** I can see chest indrawing. {description}"
                else:
                    obs = f"The chest looks normal — no indrawing detected. {description}"

                session.advance()  # -> breathing_questions
                return (
                    f"I've analyzed the chest photo.\n\n{obs}\n\n"
                    f"*(Confidence: {confidence:.0%})*\n\n"
                    "Now let me ask:\n\n"
                    "**Does your child have a cough? Is the breathing fast or noisy?**"
                )
            else:
                session.advance()
                return (
                    "I couldn't analyze the chest photo clearly.\n\n"
                    "**Does your child have a cough? Is the breathing fast or noisy?**"
                )
        elif "skip" in user_text.lower():
            session.advance()
            return "**Does your child have a cough? Is the breathing fast or noisy?**"
        else:
            return (
                "Please upload a photo of your child's chest, "
                "or type **skip** to continue with questions."
            )

    # --- BREATHING: QUESTIONS ---
    if step == "breathing_questions":
        lower = user_text.lower()

        if any(w in lower for w in ["cough", "yes", "fast", "noisy", "wheez", "difficult"]):
            session.findings["has_cough"] = True
        if any(w in lower for w in ["wheez", "whistl"]):
            session.findings["has_wheeze"] = True
        if any(w in lower for w in ["stridor", "harsh", "high pitch"]):
            session.findings["has_stridor"] = True

        # Try to extract breathing rate if mentioned
        rate = _extract_number(user_text)
        if rate and 10 <= rate <= 120:
            session.findings["breathing_rate"] = rate

        session.advance()  # -> diarrhea_photo

        return (
            "Thank you.\n\n"
            "**Step 3: Diarrhea & Dehydration**\n\n"
            "**Has your child had diarrhea (loose or watery stools)?**\n\n"
            "If yes, please also upload a photo of your child's face — "
            "I'll check for signs of dehydration like sunken eyes."
        )

    # --- DIARRHEA: PHOTO ---
    if step == "diarrhea_photo":
        lower = user_text.lower()

        if any(w in lower for w in ["no", "not", "don't", "doesn't", "hasn't"]):
            session.findings["has_diarrhea"] = False
            session.advance()  # skip diarrhea_questions
            session.advance()  # -> fever_questions
            return (
                "No diarrhea — that's good.\n\n"
                "**Step 4: Fever**\n\n"
                "**Does your child have a fever or feel hot?**"
            )

        session.findings["has_diarrhea"] = True

        if image_path:
            result = session.analyze_image(image_path, "diarrhea.assess_dehydration_signs")

            if "error" not in result:
                sunken = result.get("sunken_eyes", False)
                slow_pinch = result.get("skin_pinch_slow", False)
                session.findings["sunken_eyes"] = sunken
                session.findings["skin_pinch_slow"] = slow_pinch
                description = result.get("description", "")
                confidence = result.get("confidence", 0)

                signs = []
                if sunken:
                    signs.append("sunken eyes")
                if slow_pinch:
                    signs.append("slow skin pinch")

                if signs:
                    obs = f"**Warning:** I can see signs of dehydration: {', '.join(signs)}. {description}"
                else:
                    obs = f"No obvious dehydration signs from the photo. {description}"

                session.advance()  # -> diarrhea_questions
                return (
                    f"I've analyzed the photo.\n\n{obs}\n\n"
                    f"*(Confidence: {confidence:.0%})*\n\n"
                    "**How many days has the diarrhea lasted? Is there any blood in the stool?**"
                )

        session.advance()  # -> diarrhea_questions
        return "**How many days has the diarrhea lasted? Is there any blood in the stool?**"

    # --- DIARRHEA: QUESTIONS ---
    if step == "diarrhea_questions":
        lower = user_text.lower()

        days = _extract_number(user_text)
        if days and days > 0:
            session.findings["diarrhea_days"] = days
        if any(w in lower for w in ["blood", "bloody"]):
            session.findings["blood_in_stool"] = True

        session.advance()  # -> fever_questions

        return (
            "Thank you.\n\n"
            "**Step 4: Fever**\n\n"
            "**Does your child have a fever or feel hot? "
            "If yes, how many days has the fever lasted?**"
        )

    # --- FEVER: QUESTIONS ---
    if step == "fever_questions":
        lower = user_text.lower()

        if any(w in lower for w in ["no", "not", "doesn't", "hasn't", "don't"]):
            session.findings["has_fever"] = False
        else:
            session.findings["has_fever"] = True
            days = _extract_number(user_text)
            if days and days > 0:
                session.findings["fever_days"] = days

        if session.findings["has_fever"]:
            # Ask follow-up about malaria risk
            session.advance()  # -> nutrition_photo
            return (
                "I've noted the fever.\n\n"
                "**Does your child have a stiff neck? "
                "Are you in a malaria-risk area?**\n\n"
                "After answering, we'll move to the nutrition check."
            )
        else:
            session.advance()  # -> nutrition_photo
            return (
                "No fever — that's good.\n\n"
                "**Step 5: Nutrition**\n\n"
                "Please take a photo of your child's body — "
                "I'll check for signs of malnutrition like visible wasting.\n\n"
                "*Tap 📎 to upload a photo.*"
            )

    # --- NUTRITION: PHOTO ---
    if step == "nutrition_photo":
        # Handle fever follow-up answers if they come here
        lower = user_text.lower()
        if "stiff" in lower or "neck" in lower:
            session.findings["stiff_neck"] = "yes" in lower or "stiff" in lower
        if "malaria" in lower:
            session.findings["malaria_risk"] = any(
                w in lower for w in ["yes", "risk", "area", "endemic"]
            )

        if image_path:
            result = session.analyze_image(image_path, "nutrition.assess_wasting")

            if "error" not in result:
                wasting = result.get("visible_wasting", False)
                session.findings["visible_wasting"] = wasting
                description = result.get("description", "")
                confidence = result.get("confidence", 0)

                if wasting:
                    obs = f"**Warning:** Signs of visible wasting detected. {description}"
                else:
                    obs = f"No visible wasting detected. {description}"

                session.advance()  # -> classify
                return (
                    f"I've analyzed the photo.\n\n{obs}\n\n"
                    f"*(Confidence: {confidence:.0%})*\n\n"
                    "I now have enough information to complete the assessment. "
                    "Type **results** to see my findings."
                )

        if "skip" in lower or not image_path:
            if "skip" in lower or (user_text and not image_path):
                session.advance()  # -> classify
                return (
                    "**Assessment complete.** I have enough information.\n\n"
                    "Type **results** to see my findings and recommendations."
                )
            return (
                "**Step 5: Nutrition**\n\n"
                "Please take a photo of your child's body to check for wasting, "
                "or type **skip** to finish the assessment."
            )

    # --- CLASSIFY ---
    if step == "classify":
        classification = session.classify()
        results = classification["results"]
        overall = classification["overall_severity"]
        urgency = classification["urgency"]

        # Severity colors
        severity_marker = {
            Severity.GREEN: "🟢 GREEN",
            Severity.YELLOW: "🟡 YELLOW",
            Severity.RED: "🔴 RED",
        }

        lines = [
            "# Assessment Results\n",
            f"## Overall: {severity_marker[overall]}\n",
            f"**{urgency}**\n",
            "---\n",
            "### Findings:\n",
        ]

        for domain, classification_type, severity in results:
            label = classification_type.value.replace("_", " ").title()
            marker = severity_marker[severity]
            lines.append(f"- **{domain}**: {label} {marker}")

        lines.append("\n---\n")

        # Generate treatment with Gemma if model available
        if session.model_loaded:
            classifications_str = ", ".join(
                ct.value for _, ct, _ in results
            )
            treatment_context = (
                f"{MALAIKA_SYSTEM}\n\n"
                f"The child is {session.age_months} months old.\n"
                f"Classifications: {classifications_str}\n"
                f"Urgency: {urgency}\n\n"
                "Generate a clear, simple treatment plan for the caregiver. "
                "Use numbered steps. Include medication dosages from WHO guidelines. "
                "Include when to return immediately (danger signs to watch for). "
                "Be warm and reassuring."
            )
            treatment = session.analyze_with_gemma(
                "What should I do for my child?", treatment_context,
            )
            if treatment:
                lines.append("### Treatment Plan:\n")
                lines.append(treatment)
                lines.append("")

        lines.append("\n---\n")
        lines.append(
            "*This is decision support only — not a medical diagnosis. "
            "Always consult a health worker.*"
        )

        session.advance()  # -> complete
        return "\n".join(lines)

    # --- COMPLETE ---
    if step == "complete":
        return (
            "The assessment is complete. If you'd like to start a new assessment, "
            "please refresh the page.\n\n"
            "**Remember:** If your child gets worse — cannot drink, breathing becomes "
            "more difficult, fever increases, or the child becomes more sick — "
            "**go to a health facility immediately.**"
        )

    return "I'm not sure what happened. Please refresh and try again."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_number(text: str) -> int | None:
    """Extract the first number from a text string."""
    import re
    match = re.search(r'\b(\d+)\b', text)
    if match:
        return int(match.group(1))
    return None


# ---------------------------------------------------------------------------
# Gradio App
# ---------------------------------------------------------------------------

def create_chat_app(config: MalaikaConfig | None = None) -> Any:
    """Create the conversational Gradio chat app."""
    try:
        import gradio as gr
    except ImportError as exc:
        raise ImportError("Gradio required: pip install gradio") from exc

    if config is None:
        config = load_config()

    session = ChatSession(config)

    # Ensure prompts are registered
    from malaika.prompts import (  # noqa: F401
        PromptRegistry, breathing, danger_signs, diarrhea,
        fever, heart, nutrition, speech, system, treatment,
    )
    logger.info("prompts_loaded", count=len(PromptRegistry.list_all()))

    def respond(message: dict | str, history: list) -> str:
        """Chat response handler."""
        return process_message(message, history, session)

    def on_load() -> str:
        """Auto-load model and send welcome on app start."""
        status = session.load_model()
        logger.info("model_status", status=status)
        # Return welcome message
        return process_message("", [], session)

    chatbot = gr.Chatbot(
        value=[],
        height=500,
        type="messages",
        label="Malaika",
        avatar_images=(
            None,
            "https://em-content.zobj.net/source/twitter/408/angel_1f47c.png",
        ),
        show_copy_button=True,
    )

    with gr.Blocks(
        title="Malaika — Child Health AI",
        fill_height=True,
    ) as app:

        gr.HTML(
            '<div style="text-align:center;padding:12px;'
            'background:linear-gradient(135deg,#e8f4fd,#f0f7ff);'
            'border-bottom:3px solid #2979b9;border-radius:12px 12px 0 0;">'
            '<h1 style="margin:0;color:#1a5276;">Malaika</h1>'
            '<p style="color:#2e86c1;margin:4px 0;">Angel in Swahili — '
            'WHO IMCI Child Health AI powered by Gemma 4</p>'
            '<p style="color:#7f8c8d;font-size:0.85em;">'
            'Not for clinical use — hackathon demo</p>'
            '</div>'
        )

        chat = gr.ChatInterface(
            fn=respond,
            chatbot=chatbot,
            multimodal=True,
            textbox=gr.MultimodalTextbox(
                placeholder="Type your message or upload a photo...",
                file_count="single",
                file_types=["image"],
                sources=["upload", "webcam"],
            ),
            title=None,
            examples=[
                {"text": "Hi"},
                {"text": "My child is 12 months old"},
            ],
        )

        # Auto-load model and send welcome
        app.load(fn=on_load, outputs=[chatbot])

    return app


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Launch the Malaika chat app."""
    config = load_config()
    logger.info("malaika_chat_starting")
    app = create_chat_app(config)
    app.launch(
        share=True,
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
    )


if __name__ == "__main__":
    main()
