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
    "fever_followup",
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

    def analyze_image_direct(self, image_path: str, question: str) -> str:
        """Analyze an image with a simple question — fast, no JSON, no retries.

        Returns natural language response from Gemma 4.
        """
        if not self.model_loaded or self.inference is None:
            return ""

        try:
            messages = [
                {"role": "user", "content": [
                    {"type": "image", "image": image_path},
                    {"type": "text", "text": question},
                ]},
            ]
            return self.inference.generate(messages, max_tokens=100, temperature=0.0)
        except Exception as e:
            logger.error("image_analysis_failed", error=str(e))
            return ""

    def ask_gemma(self, question: str) -> str:
        """Ask Gemma a text-only question — fast, max 150 tokens."""
        if not self.model_loaded or self.inference is None:
            return ""

        try:
            messages = [{"role": "user", "content": question}]
            return self.inference.generate(messages, max_tokens=150, temperature=0.3)
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
            obs = session.analyze_image_direct(
                image_path,
                "Look at this child. Is the child alert, lethargic (abnormally sleepy), "
                "or unconscious? Describe briefly what you see in 1-2 sentences."
            )

            if obs:
                obs_parsed = _llm_parse_observation(session, obs, {
                    "lethargic": "Is the child lethargic (abnormally sleepy)? (true/false)",
                    "unconscious": "Is the child unconscious? (true/false)",
                })
                if obs_parsed.get("lethargic") is True:
                    session.findings["lethargic"] = True
                if obs_parsed.get("unconscious") is True:
                    session.findings["unconscious"] = True

                session.advance()
                return (
                    f"I've analyzed the photo.\n\n{obs}\n\n"
                    "**Can your child drink or breastfeed?**"
                )
            else:
                session.advance()
                return (
                    "I couldn't analyze the photo clearly.\n\n"
                    "**Can your child drink or breastfeed?**"
                )
        elif user_text.lower() == "skip":
            session.advance()
            return "**Can your child drink or breastfeed?**"
        else:
            return (
                "Please upload a photo of your child using the 📎 button, "
                "or type **skip** to continue."
            )

    # --- DANGER SIGNS: QUESTIONS ---
    if step == "danger_signs_questions":
        parsed = _llm_parse(session, user_text,
            "Can your child drink or breastfeed?",
            {
                "able_to_drink": "Is the child able to drink or breastfeed? (true/false)",
                "vomits_everything": "Does the child vomit everything they drink? (true/false)",
            })
        if parsed.get("able_to_drink") is False:
            session.findings["unable_to_drink"] = True
        if parsed.get("vomits_everything") is True:
            session.findings["vomits_everything"] = True

        session.advance()  # -> breathing_photo
        has_danger = (
            session.findings["lethargic"]
            or session.findings["unconscious"]
            or session.findings["unable_to_drink"]
            or session.findings["vomits_everything"]
        )

        if has_danger:
            danger_note = "\n\n**Warning:** I've detected some danger signs. We'll continue the full assessment."
        else:
            danger_note = "\n\nGood — no danger signs detected."

        return (
            f"Thank you.{danger_note}\n\n"
            "**Step 2: Breathing Assessment**\n\n"
            "Please take a photo of your child's **chest area**. "
            "I'll check for chest indrawing (when the lower chest pulls inward during breathing).\n\n"
            "*Upload a chest photo using 📎*"
        )

    # --- BREATHING: PHOTO ---
    if step == "breathing_photo":
        if image_path:
            obs = session.analyze_image_direct(
                image_path,
                "Look at this child's chest. Is there chest indrawing "
                "(lower chest pulling inward when breathing in)? "
                "Describe what you see in 1-2 sentences."
            )

            if obs:
                obs_parsed = _llm_parse_observation(session, obs, {
                    "chest_indrawing": "Is chest indrawing present? (true/false)",
                })
                if obs_parsed.get("chest_indrawing") is True:
                    session.findings["has_indrawing"] = True

                session.advance()
                return (
                    f"I've analyzed the chest photo.\n\n{obs}\n\n"
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
                "or type **skip** to continue."
            )

    # --- BREATHING: QUESTIONS ---
    if step == "breathing_questions":
        parsed = _llm_parse(session, user_text,
            "Does your child have a cough? Is the breathing fast or noisy?",
            {
                "has_cough": "Does the child have a cough? (true/false)",
                "fast_breathing": "Is the breathing fast or rapid? (true/false)",
                "noisy_breathing": "Is the breathing noisy, wheezy, or making unusual sounds? (true/false)",
                "breathing_rate": "Breathing rate per minute if mentioned (number or unknown)",
            })
        if parsed.get("has_cough") is True:
            session.findings["has_cough"] = True
        if parsed.get("noisy_breathing") is True:
            session.findings["has_wheeze"] = True
        rate = parsed.get("breathing_rate")
        if isinstance(rate, int) and 10 <= rate <= 120:
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
        # Check if user says no diarrhea
        parsed = _llm_parse(session, user_text,
            "Has your child had diarrhea (loose or watery stools)?",
            {"has_diarrhea": "Does the child have diarrhea? (true/false)"})
        if parsed.get("has_diarrhea") is False or _is_negative_response(user_text):
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
            obs = session.analyze_image_direct(
                image_path,
                "Look at this child's face. Are the eyes sunken? "
                "Does the child look dehydrated? Describe in 1-2 sentences."
            )

            if obs:
                obs_parsed = _llm_parse_observation(session, obs, {
                    "sunken_eyes": "Are the child's eyes sunken? (true/false)",
                    "dehydrated": "Does the child appear dehydrated? (true/false)",
                })
                if obs_parsed.get("sunken_eyes") is True:
                    session.findings["sunken_eyes"] = True
                if obs_parsed.get("dehydrated") is True:
                    session.findings["skin_pinch_slow"] = True

                session.advance()
                return (
                    f"I've analyzed the photo.\n\n{obs}\n\n"
                    "**How many days has the diarrhea lasted? Is there any blood in the stool?**"
                )

        session.advance()  # -> diarrhea_questions
        return "**How many days has the diarrhea lasted? Is there any blood in the stool?**"

    # --- DIARRHEA: QUESTIONS ---
    if step == "diarrhea_questions":
        parsed = _llm_parse(session, user_text,
            "How many days has the diarrhea lasted? Is there any blood in the stool?",
            {
                "duration_days": "How many days has the diarrhea lasted? (number or unknown)",
                "blood_in_stool": "Is there blood in the stool? (true/false)",
            })
        days = parsed.get("duration_days")
        if isinstance(days, int) and days > 0:
            session.findings["diarrhea_days"] = days
        else:
            # Fallback to number extraction
            num = _extract_number(user_text)
            if num and num > 0:
                session.findings["diarrhea_days"] = num
        if parsed.get("blood_in_stool") is True:
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
        parsed = _llm_parse(session, user_text,
            "Does your child have a fever or feel hot? How many days?",
            {
                "has_fever": "Does the child have a fever? (true/false)",
                "fever_days": "How many days has the fever lasted? (number or unknown)",
            })
        if parsed.get("has_fever") is False or _is_negative_response(user_text):
            session.findings["has_fever"] = False
            session.advance()  # -> fever_followup
            session.advance()  # -> nutrition_photo
            return (
                "No fever — that's good.\n\n"
                "**Step 5: Nutrition**\n\n"
                "Please take a photo of your child's body — "
                "I'll check for signs of malnutrition like visible wasting.\n\n"
                "*Upload a photo using 📎, or type **skip**.*"
            )
        else:
            session.findings["has_fever"] = True
            days = parsed.get("fever_days")
            if isinstance(days, int) and days > 0:
                session.findings["fever_days"] = days
            else:
                num = _extract_number(user_text)
                if num and num > 0:
                    session.findings["fever_days"] = num
            session.advance()  # -> fever_followup
            return (
                "I've noted the fever.\n\n"
                "**Does your child have a stiff neck? "
                "Are you in a malaria-risk area?**"
            )

    # --- FEVER: FOLLOW-UP ---
    if step == "fever_followup":
        parsed = _llm_parse(session, user_text,
            "Does your child have a stiff neck? Are you in a malaria-risk area?",
            {
                "stiff_neck": "Does the child have a stiff neck? (true/false)",
                "malaria_risk": "Is the family in a malaria-risk or malaria-endemic area? (true/false)",
            })
        if parsed.get("stiff_neck") is True:
            session.findings["stiff_neck"] = True
        if parsed.get("malaria_risk") is True:
            session.findings["malaria_risk"] = True

        session.advance()  # -> nutrition_photo
        return (
            "Thank you.\n\n"
            "**Step 5: Nutrition**\n\n"
            "Please take a photo of your child's body — "
            "I'll check for signs of malnutrition like visible wasting.\n\n"
            "*Upload a photo using 📎, or type **skip**.*"
        )

    # --- NUTRITION: PHOTO ---
    if step == "nutrition_photo":
        lower = user_text.lower()

        if image_path:
            obs = session.analyze_image_direct(
                image_path,
                "Look at this child's body. Is there visible wasting "
                "(very thin, ribs/bones showing)? Does the child look "
                "well-nourished or malnourished? Describe in 1-2 sentences."
            )

            if obs:
                obs_parsed = _llm_parse_observation(session, obs, {
                    "visible_wasting": "Is there visible wasting or severe thinness? (true/false)",
                    "edema": "Is there bilateral pitting edema? (true/false)",
                })
                if obs_parsed.get("visible_wasting") is True:
                    session.findings["visible_wasting"] = True
                if obs_parsed.get("edema") is True:
                    session.findings["edema"] = True

                session.advance()
                return (
                    f"I've analyzed the photo.\n\n{obs}\n\n"
                    "I now have enough information. "
                    "Type **results** to see my findings."
                )

        if "skip" in lower:
            session.advance()  # -> classify
            return (
                "**Assessment complete.** I have enough information.\n\n"
                "Type **results** to see my findings and recommendations."
            )

        return (
            "Please upload a photo of your child's body, "
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
            treatment = session.ask_gemma(
                f"You are a child health assistant. A {session.age_months}-month-old child "
                f"has these conditions: {classifications_str}. "
                f"Urgency: {urgency}. "
                "Give a simple treatment plan in numbered steps. "
                "Include WHO medication dosages. Be brief and clear."
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

def _llm_parse(session: ChatSession, user_text: str, question: str, fields: dict[str, str]) -> dict[str, bool | int | str]:
    """Use Gemma 4 to parse a caregiver's response and extract clinical findings.

    Args:
        session: ChatSession with ask_gemma available.
        user_text: What the caregiver said.
        question: What question was asked.
        fields: Dict of field_name → description to extract.
            e.g. {"able_to_drink": "Can the child drink or breastfeed?"}

    Returns:
        Dict of field_name → extracted value (True/False/number/string).
    """
    fields_desc = "\n".join(f"- {name}: {desc}" for name, desc in fields.items())
    prompt = (
        f"A caregiver was asked: \"{question}\"\n"
        f"They answered: \"{user_text}\"\n\n"
        f"Extract these facts from their answer. "
        f"Reply ONLY with one line per field in format: field_name = true/false/number\n\n"
        f"{fields_desc}\n\n"
        f"If unclear or not mentioned, write: field_name = unknown"
    )

    response = session.ask_gemma(prompt)
    if not response:
        return {}

    # Parse "field = value" lines
    result: dict[str, bool | int | str] = {}
    for line in response.strip().split("\n"):
        line = line.strip().lstrip("- ")
        if "=" not in line:
            continue
        parts = line.split("=", 1)
        if len(parts) != 2:
            continue
        name = parts[0].strip().lower().replace(" ", "_")
        val = parts[1].strip().lower()

        if val in ("true", "yes"):
            result[name] = True
        elif val in ("false", "no", "none"):
            result[name] = False
        elif val == "unknown":
            continue
        else:
            # Try as number
            num = _extract_number(val)
            if num is not None:
                result[name] = num
            else:
                result[name] = val

    logger.debug("llm_parse_result", input=user_text[:50], parsed=result)
    return result


def _llm_parse_observation(session: ChatSession, observation: str, fields: dict[str, str]) -> dict[str, bool]:
    """Use Gemma 4 to parse its OWN image observation and extract findings.

    Handles cases like "no visible wasting" → wasting=False.
    """
    fields_desc = "\n".join(f"- {name}: {desc}" for name, desc in fields.items())
    prompt = (
        f"A medical AI observed the following about a child's photo:\n"
        f"\"{observation}\"\n\n"
        f"Based on this observation, extract these findings. "
        f"Reply ONLY with one line per field: field_name = true/false\n\n"
        f"{fields_desc}"
    )

    response = session.ask_gemma(prompt)
    if not response:
        return {}

    result: dict[str, bool] = {}
    for line in response.strip().split("\n"):
        line = line.strip().lstrip("- ")
        if "=" not in line:
            continue
        parts = line.split("=", 1)
        if len(parts) != 2:
            continue
        name = parts[0].strip().lower().replace(" ", "_")
        val = parts[1].strip().lower()
        if val in ("true", "yes"):
            result[name] = True
        elif val in ("false", "no", "none"):
            result[name] = False

    return result


def _extract_number(text: str) -> int | None:
    """Extract the first number from a text string."""
    import re
    match = re.search(r'\b(\d+)\b', text)
    if match:
        return int(match.group(1))
    return None


def _has_keyword(text: str, keywords: list[str]) -> bool:
    """Check if text contains keywords WITHOUT preceding negation.

    Handles: 'no blood', 'not bloody', 'no stiff neck', 'hasn't vomited'
    Returns True only if keyword appears in an affirmative context.
    """
    lower = text.lower()
    negation_words = ["no ", "not ", "don't ", "doesn't ", "hasn't ", "haven't ",
                      "isn't ", "aren't ", "won't ", "can't ", "cannot ", "without "]

    for kw in keywords:
        if kw not in lower:
            continue
        # Find all occurrences of keyword
        idx = lower.find(kw)
        while idx != -1:
            # Check if preceded by negation within 15 chars
            prefix = lower[max(0, idx - 15):idx]
            negated = any(neg in prefix for neg in negation_words)
            if not negated:
                return True
            idx = lower.find(kw, idx + 1)
    return False


def _is_negative_response(text: str) -> bool:
    """Check if the response is a clear 'no' answer."""
    lower = text.lower().strip()
    return lower in ("no", "nope", "no.", "nah") or lower.startswith("no ") or lower.startswith("no,")


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
                sources=["upload"],
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
