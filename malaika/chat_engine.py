"""Malaika Chat Engine — conversational IMCI assessment powered by Gemma 4.

This module implements a conversation-driven clinical assessment where
Gemma 4 guides the caregiver naturally through the WHO IMCI protocol.
The model receives full conversation history and generates contextually
appropriate responses.

Architecture:
    - Gemma 4 drives the conversation (perception + communication)
    - IMCI protocol code makes clinical decisions (deterministic)
    - Session state tracks the assessment progress
    - Each response is generated with full conversation context

This module MUST NOT contain clinical thresholds or classifications.
Those belong in imci_protocol.py.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog

from malaika.config import MalaikaConfig, load_config
from malaika.types import Severity

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# IMCI Assessment Steps
# ---------------------------------------------------------------------------

ASSESSMENT_STEPS: list[str] = [
    "greeting",
    "danger_signs",
    "breathing",
    "diarrhea",
    "fever",
    "nutrition",
    "classification",
    "complete",
]

# What information each step needs to collect
STEP_REQUIREMENTS: dict[str, dict[str, str]] = {
    "greeting": {
        "age_months": "Child's age in months (2-59)",
    },
    "danger_signs": {
        "is_alert": "Is the child alert and responsive? (from photo)",
        "can_drink": "Can the child drink or breastfeed?",
        "vomits_everything": "Does the child vomit everything?",
        "has_convulsions": "Has the child had convulsions/fits?",
    },
    "breathing": {
        "has_cough": "Does the child have a cough?",
        "breathing_description": "How does the breathing sound?",
        "chest_indrawing": "Is there chest indrawing? (from photo if available)",
    },
    "diarrhea": {
        "has_diarrhea": "Does the child have diarrhea?",
        "diarrhea_days": "How many days?",
        "blood_in_stool": "Is there blood in the stool?",
        "dehydration_signs": "Signs of dehydration? (from photo if available)",
    },
    "fever": {
        "has_fever": "Does the child have fever?",
        "fever_days": "How many days?",
        "stiff_neck": "Does the child have a stiff neck?",
        "malaria_risk": "Is the family in a malaria-risk area?",
    },
    "nutrition": {
        "visible_wasting": "Is there visible wasting? (from photo if available)",
        "edema": "Is there swelling in both feet?",
    },
}


# ---------------------------------------------------------------------------
# System Prompt — The Heart of Malaika's Personality
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are Malaika, a child health assistant created to help caregivers assess their child's health using the WHO IMCI (Integrated Management of Childhood Illness) protocol.

PERSONALITY:
- You are warm, calm, and reassuring — like a trusted village health worker
- You speak simply and clearly so any caregiver can understand
- You use short sentences. You never use medical jargon unless you explain it
- You are empathetic — you acknowledge the caregiver's worry before asking questions
- You are honest about what you can and cannot see in photos

RULES:
- Always refer to the child as "your child" — never "he" or "she" unless the caregiver tells you the gender
- If the caregiver mentions gender, you may use it naturally
- NEVER diagnose. Say "based on what I can see" or "this suggests" — not "your child has"
- NEVER give medication dosages unless generating a final treatment plan
- When analyzing a photo, describe ONLY what you can actually see. Never invent observations about body parts not visible in the image
- Keep each response to 2-4 sentences unless generating the final report
- Do NOT say things like "use the clip button" or "type results" — speak naturally
- Do NOT repeat the caregiver's words back to them unnecessarily

PHOTO ANALYSIS:
- When you receive a photo, describe your specific observations
- For alertness: look at eyes (open/closed, tracking), posture, facial expression
- For chest: you CANNOT assess breathing from a still photo — be honest about this
- For dehydration: look at eyes (sunken?), skin appearance, overall alertness
- For nutrition: look at visible body fat, muscle mass, any prominent bones
- If you cannot assess something from a photo, say so and ask a clarifying question instead

ASSESSMENT FLOW:
You are guiding the caregiver through these steps in order:
1. Greeting — learn the child's age
2. Danger signs — check alertness (photo), ability to drink, convulsions
3. Breathing — check for cough, breathing problems, chest indrawing (photo optional)
4. Diarrhea — check for diarrhea, duration, blood, dehydration (photo optional)
5. Fever — check for fever, duration, stiff neck, malaria risk
6. Nutrition — check for wasting (photo optional), swelling

After each step, naturally transition to the next. Do not announce step numbers.
When you have enough information, generate the assessment results."""


# ---------------------------------------------------------------------------
# Chat Session
# ---------------------------------------------------------------------------


class ChatEngine:
    """Manages a conversational IMCI assessment session.

    Maintains conversation history, clinical findings, and assessment
    state. All responses are generated by Gemma 4 with full context.
    """

    def __init__(self, config: MalaikaConfig) -> None:
        self.config = config
        self.step = "greeting"
        self.age_months: int = 0
        self.language: str = "en"
        self.conversation_history: list[dict[str, Any]] = []

        # Clinical findings — updated by LLM extraction after each response
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

        # Model references (set externally)
        self.model: Any = None
        self.processor: Any = None
        self.model_loaded: bool = False

        # Image observations for the report
        self.observations: list[str] = []

    def process(
        self,
        user_text: str = "",
        image_path: str | None = None,
    ) -> str:
        """Process a user message and return Malaika's response.

        This is the main entry point. It:
        1. Analyzes any uploaded image with Gemma 4 vision
        2. Adds user message to conversation history
        3. Generates Malaika's response with full conversation context
        4. Extracts clinical findings from the conversation
        5. Advances the assessment step when appropriate

        Args:
            user_text: Caregiver's text message.
            image_path: Optional path to uploaded image.

        Returns:
            Malaika's response text.
        """
        # Step 1: Analyze image if provided
        image_observation = ""
        if image_path and self.model_loaded:
            image_observation = self._analyze_image(image_path)
            if image_observation:
                self.observations.append(image_observation)

        # Step 2: Build user message content
        user_content = ""
        if image_observation:
            user_content += f"[Photo uploaded. Your observation: {image_observation}]\n"
        if user_text:
            user_content += user_text
        if not user_content:
            user_content = "[User opened the app]"

        self.conversation_history.append({"role": "user", "content": user_content})

        # Step 3: Generate response with full context
        response = self._generate_response()

        self.conversation_history.append({"role": "assistant", "content": response})

        # Step 4: Extract findings from the conversation
        self._extract_findings(user_text, image_observation)

        # Step 5: Check if we should advance to next step
        self._check_step_advancement(user_text, response)

        logger.info(
            "message_processed",
            step=self.step,
            has_image=image_path is not None,
            response_length=len(response),
        )

        return response

    def _analyze_image(self, image_path: str) -> str:
        """Analyze an image with Gemma 4 vision in clinical context.

        The prompt is tailored to the current assessment step.
        """
        import torch
        from PIL import Image

        step_prompts = {
            "danger_signs": (
                "You are a child health assistant. Look at this child carefully. "
                "Describe: Are their eyes open or closed? Do they appear alert and "
                "aware of their surroundings, or do they look sleepy/unresponsive? "
                "Describe their posture and facial expression. "
                "Only describe what you can actually see."
            ),
            "breathing": (
                "You are a child health assistant. Look at this child's chest area. "
                "Can you see any signs of the lower chest pulling inward? "
                "Note: You cannot assess breathing rate or sounds from a photo. "
                "Only describe what you can actually see in the image."
            ),
            "diarrhea": (
                "You are a child health assistant. Look at this child's face. "
                "Do the eyes appear sunken or deeper than normal? "
                "Does the child's skin look dry? Does the child appear well-hydrated? "
                "Only describe what you can actually see."
            ),
            "nutrition": (
                "You are a child health assistant. Look at this child's body. "
                "Is there visible wasting (very thin, ribs or bones clearly showing)? "
                "Does the child appear well-nourished? "
                "Check for any visible swelling in the feet or legs. "
                "Only describe what you can actually see."
            ),
        }

        question = step_prompts.get(
            self.step,
            "Describe what you observe about this child's health. Only describe what you can see.",
        )

        try:
            img = Image.open(image_path).convert("RGB")
            w, h = img.size
            if max(w, h) > 512:
                scale = 512 / max(w, h)
                img = img.resize((int(w * scale), int(h * scale)))

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image"},
                        {"type": "text", "text": question},
                    ],
                }
            ]
            input_text = self.processor.apply_chat_template(
                messages, add_generation_prompt=True
            )
            inputs = self.processor(
                text=input_text, images=[img], return_tensors="pt"
            ).to(self.model.device)

            with torch.inference_mode():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=120,
                    do_sample=False,
                    repetition_penalty=1.3,
                )

            generated = outputs[0][inputs["input_ids"].shape[-1] :]
            observation = self.processor.decode(
                generated, skip_special_tokens=True
            ).strip()

            logger.info(
                "image_analyzed",
                step=self.step,
                observation_length=len(observation),
            )
            return observation

        except Exception as e:
            logger.error("image_analysis_failed", error=str(e))
            return ""

    def _generate_response(self) -> str:
        """Generate Malaika's response with full conversation history."""
        import torch

        if not self.model_loaded:
            return self._fallback_response()

        # Build the step-specific context
        step_context = self._build_step_context()

        system_content = f"{SYSTEM_PROMPT}\n\n{step_context}"

        messages = [{"role": "system", "content": system_content}]
        messages.extend(self.conversation_history)

        try:
            input_text = self.processor.apply_chat_template(
                messages, add_generation_prompt=True
            )
            inputs = self.processor(
                text=input_text, return_tensors="pt"
            ).to(self.model.device)

            with torch.inference_mode():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=250,
                    do_sample=True,
                    temperature=0.4,
                    repetition_penalty=1.3,
                )

            generated = outputs[0][inputs["input_ids"].shape[-1] :]
            return self.processor.decode(
                generated, skip_special_tokens=True
            ).strip()

        except Exception as e:
            logger.error("response_generation_failed", error=str(e))
            return self._fallback_response()

    def _build_step_context(self) -> str:
        """Build step-specific context for the system prompt."""
        if self.step == "greeting":
            return "You are starting a new assessment. Greet the caregiver warmly and ask the child's age in months."

        if self.step == "classification":
            return self._build_classification_context()

        if self.step == "complete":
            return (
                "The assessment is complete. If the caregiver asks anything, "
                "remind them of the key findings and to seek help if the child gets worse."
            )

        # For assessment steps, tell Gemma what to focus on
        context = f"You are currently assessing: {self.step.replace('_', ' ')}.\n"

        collected = []
        needed = []
        requirements = STEP_REQUIREMENTS.get(self.step, {})

        for field, description in requirements.items():
            if self._is_field_collected(field):
                collected.append(f"  - {description}: COLLECTED")
            else:
                needed.append(f"  - {description}: STILL NEEDED")

        if collected:
            context += "Already collected:\n" + "\n".join(collected) + "\n"
        if needed:
            context += "Still need to collect:\n" + "\n".join(needed) + "\n"
        else:
            context += "All information collected for this step. Naturally transition to the next topic.\n"

        return context

    def _is_field_collected(self, field: str) -> bool:
        """Check if a clinical field has been collected."""
        field_mapping: dict[str, str] = {
            "age_months": "age_months",
            "is_alert": "lethargic",
            "can_drink": "unable_to_drink",
            "vomits_everything": "vomits_everything",
            "has_convulsions": "has_convulsions",
            "has_cough": "has_cough",
            "chest_indrawing": "has_indrawing",
            "has_diarrhea": "has_diarrhea",
            "diarrhea_days": "diarrhea_days",
            "blood_in_stool": "blood_in_stool",
            "dehydration_signs": "sunken_eyes",
            "has_fever": "has_fever",
            "fever_days": "fever_days",
            "stiff_neck": "stiff_neck",
            "malaria_risk": "malaria_risk",
            "visible_wasting": "visible_wasting",
            "edema": "edema",
            "breathing_description": "has_cough",
        }

        finding_key = field_mapping.get(field, field)

        if field == "age_months":
            return self.age_months > 0

        if finding_key in self.findings:
            val = self.findings[finding_key]
            return val is not None and val is not False and val != 0

        return False

    def _extract_findings(self, user_text: str, image_observation: str) -> None:
        """Extract clinical findings from user text and image observations.

        Uses Gemma 4 to understand the caregiver's responses in context.
        """
        import torch

        combined = ""
        if user_text:
            combined += f"Caregiver said: {user_text}\n"
        if image_observation:
            combined += f"Image observation: {image_observation}\n"

        if not combined.strip() or not self.model_loaded:
            return

        # Extract age from greeting step
        if self.step == "greeting":
            import re

            match = re.search(r'\b(\d+)\b', user_text)
            if match:
                age = int(match.group(1))
                if 2 <= age <= 59:
                    self.age_months = age
            return

        # For clinical steps, use LLM to extract findings
        extraction_prompt = (
            f"Extract clinical findings from this interaction.\n\n"
            f"Current step: {self.step}\n"
            f"{combined}\n"
            f"For each finding below, write: finding = true/false/number/unknown\n\n"
        )

        step_fields: dict[str, list[str]] = {
            "danger_signs": [
                "lethargic (child is abnormally sleepy)",
                "unconscious (child cannot be woken)",
                "unable_to_drink (child cannot drink or breastfeed)",
                "vomits_everything (child vomits everything ingested)",
                "has_convulsions (child has had fits or seizures)",
            ],
            "breathing": [
                "has_cough (child has a cough)",
                "has_wheeze (breathing has whistling/wheezing sound)",
                "has_stridor (harsh high-pitched breathing sound)",
                "has_indrawing (lower chest pulls inward when breathing)",
            ],
            "diarrhea": [
                "has_diarrhea (child has loose/watery stools)",
                "diarrhea_days (number of days diarrhea has lasted)",
                "blood_in_stool (blood visible in stool)",
                "sunken_eyes (child's eyes appear sunken)",
                "skin_pinch_slow (skin pinch returns slowly)",
            ],
            "fever": [
                "has_fever (child has fever or feels hot)",
                "fever_days (number of days of fever)",
                "stiff_neck (child has a stiff neck)",
                "malaria_risk (family lives in malaria-endemic area)",
            ],
            "nutrition": [
                "visible_wasting (child appears very thin with visible ribs/bones)",
                "edema (swelling in both feet)",
            ],
        }

        fields = step_fields.get(self.step, [])
        if not fields:
            return

        extraction_prompt += "\n".join(f"- {f}" for f in fields)

        try:
            inputs = self.processor(
                text=extraction_prompt, return_tensors="pt"
            ).to(self.model.device)

            with torch.inference_mode():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=100,
                    do_sample=False,
                    repetition_penalty=1.3,
                )

            generated = outputs[0][inputs["input_ids"].shape[-1] :]
            result = self.processor.decode(generated, skip_special_tokens=True).strip()

            # Parse "finding = value" lines
            for line in result.split("\n"):
                line = line.strip().lstrip("- ")
                if "=" not in line:
                    continue
                parts = line.split("=", 1)
                name = parts[0].strip().lower().replace(" ", "_").split("(")[0].strip().rstrip("_")
                val = parts[1].strip().lower()

                if name in self.findings:
                    if val in ("true", "yes"):
                        self.findings[name] = True
                    elif val in ("false", "no", "none"):
                        self.findings[name] = False
                    elif val != "unknown":
                        import re

                        num = re.search(r'\d+', val)
                        if num:
                            self.findings[name] = int(num.group())

            logger.debug("findings_extracted", step=self.step, findings=result[:200])

        except Exception as e:
            logger.error("finding_extraction_failed", error=str(e))

    def _check_step_advancement(self, user_text: str, response: str) -> None:
        """Advance step only when the user has provided substantive responses.

        Each step requires at least one real user message (not the initial "Hi").
        Steps only advance based on actual findings or explicit user answers.
        """
        # Count real user messages (not "Hi" or system messages)
        user_msgs_in_step = self._count_user_msgs_since_step_start()

        if self.step == "greeting" and self.age_months > 0:
            self.step = "danger_signs"
            self._step_start_msg_count = len(self.conversation_history)
        elif self.step == "danger_signs" and user_msgs_in_step >= 2:
            # Need at least: photo response + drink/convulsions answer
            self.step = "breathing"
            self._step_start_msg_count = len(self.conversation_history)
        elif self.step == "breathing" and user_msgs_in_step >= 1:
            self.step = "diarrhea"
            self._step_start_msg_count = len(self.conversation_history)
        elif self.step == "diarrhea" and user_msgs_in_step >= 1:
            self.step = "fever"
            self._step_start_msg_count = len(self.conversation_history)
        elif self.step == "fever" and user_msgs_in_step >= 1:
            self.step = "nutrition"
            self._step_start_msg_count = len(self.conversation_history)
        elif self.step == "nutrition" and user_msgs_in_step >= 1:
            self.step = "classification"
            self._step_start_msg_count = len(self.conversation_history)
        elif self.step == "classification":
            self.step = "complete"

    _step_start_msg_count: int = 0

    def _count_user_msgs_since_step_start(self) -> int:
        """Count user messages since the current step started."""
        count = 0
        for msg in self.conversation_history[self._step_start_msg_count:]:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                # Don't count system-generated messages
                if content and not content.startswith("["):
                    count += 1
        return count

    def _build_classification_context(self) -> str:
        """Build the classification report with reasoning."""
        from malaika.imci_protocol import (
            classify_breathing,
            classify_danger_signs,
            classify_diarrhea,
            classify_fever,
            classify_nutrition,
        )

        results: list[dict[str, Any]] = []

        # Danger signs
        ds = classify_danger_signs(
            lethargic=self.findings["lethargic"],
            unconscious=self.findings["unconscious"],
            unable_to_drink=self.findings["unable_to_drink"],
            vomits_everything=self.findings["vomits_everything"],
        )
        if ds:
            results.append({
                "domain": "Danger Signs",
                "classification": ds.classification.value,
                "severity": ds.severity.value,
                "reasoning": self._danger_sign_reasoning(),
            })

        # Breathing
        br = classify_breathing(
            age_months=self.age_months,
            has_cough=self.findings["has_cough"],
            breathing_rate=self.findings["breathing_rate"],
            has_indrawing=self.findings["has_indrawing"],
            has_stridor=self.findings["has_stridor"],
            has_wheeze=self.findings["has_wheeze"],
        )
        results.append({
            "domain": "Breathing",
            "classification": br.classification.value,
            "severity": br.severity.value,
            "reasoning": self._breathing_reasoning(),
        })

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
                results.append({
                    "domain": "Diarrhea",
                    "classification": dd.classification.value,
                    "severity": dd.severity.value,
                    "reasoning": self._diarrhea_reasoning(),
                })

        # Fever
        if self.findings["has_fever"]:
            fv = classify_fever(
                has_fever=True,
                duration_days=self.findings["fever_days"],
                stiff_neck=self.findings["stiff_neck"],
                malaria_risk=self.findings["malaria_risk"],
            )
            if fv:
                results.append({
                    "domain": "Fever",
                    "classification": fv.classification.value,
                    "severity": fv.severity.value,
                    "reasoning": self._fever_reasoning(),
                })

        # Nutrition
        nt = classify_nutrition(
            visible_wasting=self.findings["visible_wasting"],
            edema=self.findings["edema"],
            muac_mm=self.findings["muac_mm"],
        )
        results.append({
            "domain": "Nutrition",
            "classification": nt.classification.value,
            "severity": nt.severity.value,
            "reasoning": self._nutrition_reasoning(),
        })

        # Overall severity
        severities = [r["severity"] for r in results]
        if "red" in severities:
            overall = "RED"
            urgency = "URGENT: Go to a health facility IMMEDIATELY"
        elif "yellow" in severities:
            overall = "YELLOW"
            urgency = "See a health worker within 24 hours"
        else:
            overall = "GREEN"
            urgency = "Treat at home with follow-up in 5 days"

        # Build context for Gemma to present naturally
        report_data = json.dumps({
            "child_age_months": self.age_months,
            "overall_severity": overall,
            "urgency": urgency,
            "findings": results,
            "observations": self.observations,
        }, indent=2)

        return (
            "The assessment is now complete. Present the results to the caregiver.\n\n"
            "IMPORTANT: Use the exact classifications and severity levels below. "
            "Do NOT change any medical classification. Present them clearly with reasoning.\n\n"
            f"Assessment data:\n{report_data}\n\n"
            "Format the response as:\n"
            "1. Overall severity (use the emoji: GREEN, YELLOW, or RED)\n"
            "2. Urgency message\n"
            "3. Each finding with its classification, severity, and reasoning\n"
            "4. A simple treatment plan based on WHO IMCI guidelines\n"
            "5. When to return immediately (danger signs to watch for)\n\n"
            "Be caring and clear. This caregiver needs actionable guidance."
        )

    # --- Reasoning Helpers ---

    def _danger_sign_reasoning(self) -> str:
        reasons = []
        if self.findings["lethargic"]:
            reasons.append("Child appears lethargic")
        if self.findings["unconscious"]:
            reasons.append("Child appears unconscious")
        if self.findings["unable_to_drink"]:
            reasons.append("Child unable to drink or breastfeed")
        if self.findings["vomits_everything"]:
            reasons.append("Child vomits everything")
        if self.findings["has_convulsions"]:
            reasons.append("Child has had convulsions")
        return "; ".join(reasons) if reasons else "No danger signs detected"

    def _breathing_reasoning(self) -> str:
        reasons = []
        if self.findings["has_cough"]:
            reasons.append("Cough present")
        if self.findings["has_wheeze"]:
            reasons.append("Wheezing/noisy breathing reported")
        if self.findings["has_indrawing"]:
            reasons.append("Chest indrawing observed")
        if self.findings["breathing_rate"]:
            reasons.append(f"Breathing rate: {self.findings['breathing_rate']}/min")
        return "; ".join(reasons) if reasons else "No breathing concerns"

    def _diarrhea_reasoning(self) -> str:
        reasons = []
        if self.findings["has_diarrhea"]:
            reasons.append(f"Diarrhea for {self.findings['diarrhea_days']} days")
        if self.findings["blood_in_stool"]:
            reasons.append("Blood in stool")
        if self.findings["sunken_eyes"]:
            reasons.append("Sunken eyes observed")
        return "; ".join(reasons) if reasons else "No diarrhea"

    def _fever_reasoning(self) -> str:
        reasons = []
        if self.findings["has_fever"]:
            reasons.append(f"Fever for {self.findings['fever_days']} days")
        if self.findings["stiff_neck"]:
            reasons.append("Stiff neck present")
        if self.findings["malaria_risk"]:
            reasons.append("In malaria-risk area")
        return "; ".join(reasons) if reasons else "No fever"

    def _nutrition_reasoning(self) -> str:
        reasons = []
        if self.findings["visible_wasting"]:
            reasons.append("Visible wasting observed")
        if self.findings["edema"]:
            reasons.append("Bilateral edema present")
        return "; ".join(reasons) if reasons else "No malnutrition signs"

    def _fallback_response(self) -> str:
        """Generate a basic response when the model is not available."""
        if self.step == "greeting":
            return "Hello, I am Malaika. How old is your child in months?"
        return "I am having trouble processing right now. Please try again."

    def reset(self) -> None:
        """Reset the session for a new assessment."""
        self.step = "greeting"
        self.age_months = 0
        self.conversation_history.clear()
        self.observations.clear()
        self.findings = {k: (False if isinstance(v, bool) else (0 if isinstance(v, int) else None))
                        for k, v in self.findings.items()}
        logger.info("session_reset")
