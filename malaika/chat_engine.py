"""Malaika Chat Engine — agentic IMCI assessment powered by Gemma 4.

This module implements a skill-driven clinical assessment agent where
Gemma 4 orchestrates 12 specialized clinical skills through the WHO IMCI
protocol. The agent maintains a belief state, invokes skills for perception,
and emits structured events for the UI.

Architecture:
    - IMCI Protocol Guard enforces step ordering (deterministic)
    - Gemma 4 drives conversation + selects skills (agentic reasoning)
    - Skills provide structured perception (vision, audio, speech parsing)
    - imci_protocol.py makes clinical classifications (deterministic code)
    - BeliefState tracks confirmed/uncertain/pending findings

This module MUST NOT contain clinical thresholds or classifications.
Those belong in imci_protocol.py.
"""

from __future__ import annotations

import json
import re
from typing import Any

import structlog

from malaika.config import MalaikaConfig
from malaika.skills import BeliefState, SkillRegistry, SkillResult

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

# Clinical steps that have assessable content (index for progress bar)
CLINICAL_STEPS: list[str] = [
    "danger_signs",
    "breathing",
    "diarrhea",
    "fever",
    "nutrition",
]

# Required fields per step — step only advances when these are in _fields_answered
STEP_REQUIRED_FIELDS: dict[str, set[str]] = {
    "danger_signs": {"can_drink", "vomits_everything", "has_convulsions"},
    "breathing": {"has_cough"},
    "diarrhea": {"has_diarrhea"},
    "fever": {"has_fever"},
    "nutrition": {"visible_wasting", "edema"},
}

# Conditional fields — required only if a trigger finding is True
STEP_CONDITIONAL_FIELDS: dict[str, dict[str, set[str]]] = {
    "diarrhea": {"has_diarrhea": {"diarrhea_days", "blood_in_stool"}},
    "fever": {"has_fever": {"fever_days", "malaria_risk"}},
}

# What information each step needs to collect (for system prompt context)
STEP_REQUIREMENTS: dict[str, dict[str, str]] = {
    "greeting": {
        "age_months": "Child's age in months (2-59)",
    },
    "danger_signs": {
        "is_alert": "Is the child very sleepy or hard to wake up?",
        "can_drink": "Is the child unable to drink or breastfeed?",
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

# Image request prompts per step
IMAGE_REQUEST_PROMPTS: dict[str, dict[str, str]] = {
    "danger_signs": {
        "skill": "assess_alertness",
        "prompt": "Can you hold the phone so I can see your child? I want to check how alert they are.",
    },
    "breathing": {
        "skill": "detect_chest_indrawing",
        "prompt": "Can you take a photo of your child's chest area? I want to check their breathing.",
    },
    "diarrhea": {
        "skill": "assess_dehydration_signs",
        "prompt": "Can you take a close photo of your child's face? I want to check for signs of dehydration.",
    },
    "nutrition": {
        "skill": "assess_wasting",
        "prompt": "Can you take a photo showing your child's body? I want to check their nutrition.",
    },
}


# ---------------------------------------------------------------------------
# System Prompt — The Heart of Malaika's Personality
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are Malaika, an AI child health agent that helps caregivers assess their child's health using the WHO IMCI (Integrated Management of Childhood Illness) protocol.

You are NOT a chatbot. You are a clinical assessment agent with specialized skills for analyzing photos, sounds, and symptoms. You invoke these skills to build a structured clinical picture, then apply WHO IMCI classification logic to produce actionable guidance.

PERSONALITY:
- You are warm, calm, and reassuring — like a trusted village health worker
- You speak simply and clearly so any caregiver can understand
- You use short sentences. You never use medical jargon unless you explain it
- You are empathetic — you acknowledge the caregiver's worry before asking questions
- You are honest about what you can and cannot see in photos

RULES:
- Ask ONE question at a time. Do NOT bundle multiple questions together
- Do NOT skip required questions for the current step — ask ALL of them before moving on
- Always refer to the child as "your child" — never "he" or "she" unless the caregiver tells you the gender
- If the caregiver mentions gender, you may use it naturally
- NEVER diagnose. Say "based on what I can see" or "this suggests" — not "your child has"
- NEVER give medication dosages unless generating a final treatment plan
- When analyzing a photo, describe ONLY what you can actually see. Never invent observations
- Keep each response to 2-3 sentences unless generating the final report
- Do NOT say things like "use the clip button" or "type results" — speak naturally
- Do NOT repeat the caregiver's words back to them unnecessarily

QUESTION PHRASING:
- Always phrase symptom questions so that "yes" means the symptom IS PRESENT
- Alertness: ask "Is your child very sleepy or hard to wake up?" (not "Is your child alert?")
- Drinking: ask "Is your child unable to drink?" (not "Can your child drink?")
- This ensures caregiver "yes"/"no" answers are unambiguous
- For age: "How old is your child in months?" is fine as-is

PHOTO ANALYSIS:
- When you receive a photo, describe your specific observations to the caregiver
- For alertness: look at eyes (open/closed, tracking), posture, facial expression
- For chest: you CANNOT assess breathing from a still photo — be honest about this
- For dehydration: look at eyes (sunken?), skin appearance, overall alertness
- For nutrition: look at visible body fat, muscle mass, any prominent bones
- If you cannot assess something from a photo, say so and ask a clarifying question

ASSESSMENT FLOW:
You are guiding the caregiver through these steps in order:
1. Greeting — learn the child's age
2. Danger signs — check alertness (photo), ability to drink, vomiting, convulsions
3. Breathing — check for cough, breathing problems, chest indrawing (photo optional)
4. Diarrhea — check for diarrhea, duration, blood, dehydration (photo optional)
5. Fever — check for fever, duration, stiff neck, malaria risk
6. Nutrition — check for wasting (photo optional), swelling in feet

After each step, naturally transition to the next. Do not announce step numbers.
When you have enough information, generate the assessment results."""


# ---------------------------------------------------------------------------
# Chat Engine — Agentic IMCI Assessment
# ---------------------------------------------------------------------------


class ChatEngine:
    """Manages a skill-driven conversational IMCI assessment session.

    Maintains conversation history, belief state, clinical findings, and
    assessment state. Emits structured events for the UI alongside voice
    responses.
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

        # Agent state
        self.belief = BeliefState()
        self._fields_answered: set[str] = set()
        self._image_received_this_step: bool = False
        self._step_start_msg_count: int = 0
        self._step_message_nudge_threshold: int = 5

        # Model references (set externally)
        self.model: Any = None
        self.processor: Any = None
        self.model_loaded: bool = False

        # Image observations for the report
        self.observations: list[str] = []

        # Requirement field name of the question most recently posed by the LLM.
        # Used for yes/no disambiguation when caregiver gives a brief response.
        self._pending_question_topic: str | None = None

    def process(
        self,
        user_text: str = "",
        image_path: str | None = None,
    ) -> dict[str, Any]:
        """Process a user message and return Malaika's response with events.

        This is the main agent entry point. It:
        1. Invokes vision skill if image provided (emits skill_invoked/skill_result)
        2. Parses caregiver text to extract clinical findings (emits finding events)
        3. Generates Malaika's conversational response
        4. Checks step advancement (emits step_change, classification events)
        5. Requests images if needed (emits image_request events)

        Args:
            user_text: Caregiver's text message.
            image_path: Optional path to uploaded image.

        Returns:
            Dict with "text" (voice response) and "events" (list of UI events).
        """
        events: list[dict[str, Any]] = []

        # Step 1: Analyze image if provided — invoke vision skill
        image_observation = ""
        if image_path and self.model_loaded:
            self._image_received_this_step = True
            skill_name = self._get_vision_skill_for_step()
            events.append({
                "type": "skill_invoked",
                "skill": skill_name,
                "description": f"Analyzing photo with {skill_name.replace('_', ' ')}...",
                "input_type": "image",
            })

            image_observation = self._analyze_image(image_path)
            if image_observation:
                self.observations.append(image_observation)
                self.belief.mark_skill_invoked(skill_name)
                events.append({
                    "type": "skill_result",
                    "skill": skill_name,
                    "findings": {},
                    "confidence": 0.8,
                    "description": image_observation,
                })

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

        # Step 4: Extract findings from conversation — emits finding events
        self._extract_findings(user_text, image_observation, events)

        # Step 5: Check if we should advance to next step — emits step/classification events
        self._check_step_advancement(events)

        # Step 6: Maybe request an image for the current step
        self._maybe_request_image(events)

        logger.info(
            "agent_processed",
            step=self.step,
            has_image=image_path is not None,
            response_length=len(response),
            events_count=len(events),
            fields_answered=len(self._fields_answered),
            severity=self.belief.current_severity,
        )

        return {"text": response, "events": events}

    # -------------------------------------------------------------------
    # Vision Skill Invocation
    # -------------------------------------------------------------------

    def _get_vision_skill_for_step(self) -> str:
        """Get the appropriate vision skill name for the current step."""
        step_skills: dict[str, str] = {
            "danger_signs": "assess_alertness",
            "breathing": "detect_chest_indrawing",
            "diarrhea": "assess_dehydration_signs",
            "nutrition": "assess_wasting",
        }
        return step_skills.get(self.step, "assess_alertness")

    def _analyze_image(self, image_path: str) -> str:
        """Analyze an image with Gemma 4 vision in clinical context."""
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

            generated = outputs[0][inputs["input_ids"].shape[-1]:]
            observation = self.processor.decode(
                generated, skip_special_tokens=True
            ).strip()

            logger.info("image_analyzed", step=self.step, observation_length=len(observation))
            return observation

        except Exception as e:
            logger.error("image_analysis_failed", error=str(e))
            return ""

    # -------------------------------------------------------------------
    # Response Generation
    # -------------------------------------------------------------------

    def _generate_response(self) -> str:
        """Generate Malaika's response with full conversation history."""
        import torch

        if not self.model_loaded:
            return self._fallback_response()

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

            generated = outputs[0][inputs["input_ids"].shape[-1]:]
            return self.processor.decode(generated, skip_special_tokens=True).strip()

        except Exception as e:
            logger.error("response_generation_failed", error=str(e))
            return self._fallback_response()

    def _build_step_context(self) -> str:
        """Build step-specific context with skill descriptions and belief state."""
        if self.step == "greeting":
            return "You are starting a new assessment. Greet the caregiver warmly and ask the child's age in months."

        if self.step == "classification":
            return self._build_classification_context()

        if self.step == "complete":
            return (
                "The assessment is complete. If the caregiver asks anything, "
                "remind them of the key findings and to seek help if the child gets worse."
            )

        # Build skill-aware context for clinical steps
        context = f"You are currently assessing: {self.step.replace('_', ' ')}.\n"

        # Show available skills
        skill_desc = SkillRegistry.as_tool_descriptions(self.step)
        context += f"\n{skill_desc}\n\n"

        # Show what's collected and what's still needed
        collected = []
        needed = []
        requirements = STEP_REQUIREMENTS.get(self.step, {})

        for field_key, description in requirements.items():
            if field_key in self._fields_answered or self._is_field_collected(field_key):
                collected.append(f"  - {description}: COLLECTED")
            else:
                needed.append(f"  - {description}: STILL NEEDED")

        # Track what we're about to ask about (for yes/no disambiguation next turn)
        self._pending_question_topic = None
        for field_key in requirements:
            if field_key not in self._fields_answered and not self._is_field_collected(field_key):
                self._pending_question_topic = field_key
                break

        if collected:
            context += "Already collected:\n" + "\n".join(collected) + "\n"
        if needed:
            context += "Still need to collect:\n" + "\n".join(needed) + "\n"
            context += "\nIMPORTANT: Ask about the NEXT uncollected item. Ask ONE question at a time.\n"
        else:
            context += "All information collected for this step. Naturally transition to the next topic.\n"

        # Show belief state summary
        if self.belief.confirmed:
            confirmed_str = ", ".join(
                f"{k}={v}" for k, v in self.belief.confirmed.items()
                if v is not False and v is not None and v != 0
            )
            if confirmed_str:
                context += f"\nConfirmed findings so far: {confirmed_str}\n"

        # Nudge if stuck
        msgs_in_step = self._count_user_msgs_since_step_start()
        if msgs_in_step >= self._step_message_nudge_threshold and needed:
            context += (
                "\nNOTE: The caregiver has been answering for a while. "
                "Ask the remaining questions more directly.\n"
            )

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

    # -------------------------------------------------------------------
    # Finding Extraction — Skill: parse_caregiver_response
    # -------------------------------------------------------------------

    def _extract_findings(
        self,
        user_text: str,
        image_observation: str,
        events: list[dict[str, Any]],
    ) -> None:
        """Extract clinical findings from user text and image observations.

        Uses Gemma 4 to understand the caregiver's responses in context.
        Emits finding events for each detected finding.
        """
        import torch

        # Extract age from greeting step (doesn't need model)
        if self.step == "greeting":
            if user_text:
                age = self._extract_age(user_text)
                if age and 2 <= age <= 59:
                    self.age_months = age
                    self.belief.confirm_finding("age_months", age)
            return

        # --- Yes/No context disambiguation ---
        # When the caregiver gives a brief yes/no, map it to the finding
        # that was most recently asked about. This handles bare "yes"/"no"
        # which the LLM extraction might not see in isolation.
        if user_text and self._pending_question_topic:
            user_lower = user_text.strip().lower()
            is_yes = bool(self._YES_PATTERN.match(user_lower))
            is_no = bool(self._NO_PATTERN.match(user_lower))
            if is_yes or is_no:
                mapping = self._YES_NO_MAPPINGS.get(self._pending_question_topic)
                if mapping:
                    finding_key, yes_val, no_val, satisfies = mapping
                    value = yes_val if is_yes else no_val
                    self.findings[finding_key] = value
                    self._fields_answered.add(finding_key)
                    self.belief.confirm_finding(finding_key, value)
                    for field in satisfies:
                        self._fields_answered.add(field)
                    events.append({
                        "type": "finding",
                        "key": finding_key,
                        "value": value,
                        "label": finding_key.replace("_", " ").title(),
                    })

        combined = ""
        if user_text:
            combined += f"Caregiver said: {user_text}\n"
        if image_observation:
            combined += f"Image observation: {image_observation}\n"

        if not combined.strip() or not self.model_loaded:
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

            generated = outputs[0][inputs["input_ids"].shape[-1]:]
            result = self.processor.decode(generated, skip_special_tokens=True).strip()

            # Parse "finding = value" lines and emit events
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
                        self._fields_answered.add(name)
                        self.belief.confirm_finding(name, True)
                        events.append({
                            "type": "finding",
                            "key": name,
                            "value": True,
                            "label": name.replace("_", " ").title(),
                        })
                    elif val in ("false", "no", "none"):
                        self.findings[name] = False
                        self._fields_answered.add(name)
                        self.belief.confirm_finding(name, False)
                        events.append({
                            "type": "finding",
                            "key": name,
                            "value": False,
                            "label": name.replace("_", " ").title(),
                        })
                    elif val != "unknown":
                        num = re.search(r'\d+', val)
                        if num:
                            numeric_val = int(num.group())
                            self.findings[name] = numeric_val
                            self._fields_answered.add(name)
                            self.belief.confirm_finding(name, numeric_val)
                            events.append({
                                "type": "finding",
                                "key": name,
                                "value": numeric_val,
                                "label": name.replace("_", " ").title(),
                            })
                    else:
                        self.belief.mark_uncertain(name, "LLM could not determine")

            # Map answered fields to step requirement names
            field_to_requirement: dict[str, str] = {
                "unable_to_drink": "can_drink",
                "has_cough": "has_cough",
                "has_diarrhea": "has_diarrhea",
                "diarrhea_days": "diarrhea_days",
                "blood_in_stool": "blood_in_stool",
                "has_fever": "has_fever",
                "fever_days": "fever_days",
                "stiff_neck": "stiff_neck",
                "malaria_risk": "malaria_risk",
                "visible_wasting": "visible_wasting",
                "edema": "edema",
                "vomits_everything": "vomits_everything",
                "has_convulsions": "has_convulsions",
                "lethargic": "is_alert",
            }
            for finding_name in self._fields_answered:
                req_name = field_to_requirement.get(finding_name, finding_name)
                self._fields_answered.add(req_name)

            logger.debug("findings_extracted", step=self.step, findings=result[:200])

        except Exception as e:
            logger.error("finding_extraction_failed", error=str(e))

    # -------------------------------------------------------------------
    # Step Advancement — Findings-Based
    # -------------------------------------------------------------------

    # Yes/No disambiguation: maps requirement field -> (finding_key, yes_value, no_value, satisfies)
    # All questions are phrased so "yes" = symptom present (see QUESTION PHRASING in system prompt).
    _YES_NO_MAPPINGS: dict[str, tuple[str, bool, bool, list[str]]] = {
        "is_alert": ("lethargic", True, False, ["is_alert"]),
        "can_drink": ("unable_to_drink", True, False, ["can_drink"]),
        "vomits_everything": ("vomits_everything", True, False, ["vomits_everything"]),
        "has_convulsions": ("has_convulsions", True, False, ["has_convulsions"]),
        "has_cough": ("has_cough", True, False, ["has_cough"]),
        "has_diarrhea": ("has_diarrhea", True, False, ["has_diarrhea"]),
        "blood_in_stool": ("blood_in_stool", True, False, ["blood_in_stool"]),
        "has_fever": ("has_fever", True, False, ["has_fever"]),
        "stiff_neck": ("stiff_neck", True, False, ["stiff_neck"]),
        "malaria_risk": ("malaria_risk", True, False, ["malaria_risk"]),
        "visible_wasting": ("visible_wasting", True, False, ["visible_wasting"]),
        "edema": ("edema", True, False, ["edema"]),
    }

    _YES_PATTERN = re.compile(
        r"^(yes|yeah|yep|ya|yah|correct|right|sure|ok|uh[ -]?huh|definitely|absolutely)\b",
        re.IGNORECASE,
    )
    _NO_PATTERN = re.compile(
        r"^(no|nah|nope|not really|never|none|not at all|neither)\b",
        re.IGNORECASE,
    )

    # Minimum messages before message-count fallback can trigger
    _MSG_FALLBACK_THRESHOLDS: dict[str, int] = {
        "danger_signs": 3,
        "breathing": 2,
        "diarrhea": 2,
        "fever": 2,
        "nutrition": 2,
    }

    def _check_step_advancement(self, events: list[dict[str, Any]]) -> None:
        """Advance step when required findings are collected OR enough messages exchanged.

        Primary: findings-based (all required fields in _fields_answered).
        Fallback: message-count (after N user messages, advance anyway).
        This ensures the progress bar always moves even if LLM extraction
        is imperfect.
        """
        if self.step == "greeting" and self.age_months > 0:
            self._advance_to("danger_signs", events)
            return

        if self.step == "classification":
            self._advance_to("complete", events)
            return

        if self.step not in STEP_REQUIRED_FIELDS:
            return

        should_advance = False

        # Primary: findings-based check
        required = STEP_REQUIRED_FIELDS[self.step]
        if required.issubset(self._fields_answered):
            # Also check conditional fields
            conditionals = STEP_CONDITIONAL_FIELDS.get(self.step, {})
            conditions_met = True
            for trigger_field, extra_fields in conditionals.items():
                if self.findings.get(trigger_field):
                    if not extra_fields.issubset(self._fields_answered):
                        conditions_met = False
                        break
            if conditions_met:
                should_advance = True

        # Fallback: message-count based (ensures progress bar always moves)
        if not should_advance:
            threshold = self._MSG_FALLBACK_THRESHOLDS.get(self.step, 3)
            msgs = self._count_user_msgs_since_step_start()
            if msgs >= threshold:
                should_advance = True
                logger.info(
                    "step_advance_fallback",
                    step=self.step,
                    messages=msgs,
                    threshold=threshold,
                    fields_answered=list(self._fields_answered),
                )

        if not should_advance:
            return

        # Advance to next step
        step_index = ASSESSMENT_STEPS.index(self.step)
        next_step = ASSESSMENT_STEPS[step_index + 1]
        self._advance_to(next_step, events)

    def _advance_to(self, new_step: str, events: list[dict[str, Any]]) -> None:
        """Advance to a new IMCI step, running classification on the old step."""
        old_step = self.step

        # Run per-step classification BEFORE advancing
        if old_step in CLINICAL_STEPS:
            classification_event = self._classify_completed_step(old_step)
            if classification_event:
                events.append(classification_event)

        # Advance
        self.step = new_step
        self._step_start_msg_count = len(self.conversation_history)
        self._image_received_this_step = False
        self.belief.reset_for_step()

        # Emit step change event
        if new_step in CLINICAL_STEPS:
            step_index = CLINICAL_STEPS.index(new_step)
            events.append({
                "type": "step_change",
                "step": new_step,
                "index": step_index + 1,
                "total": len(CLINICAL_STEPS),
                "label": new_step.replace("_", " ").title(),
            })
        elif new_step == "classification":
            # Emit assessment complete
            self._emit_assessment_complete(events)

        logger.info(
            "step_advanced",
            from_step=old_step,
            to_step=new_step,
            severity=self.belief.current_severity,
        )

    # -------------------------------------------------------------------
    # Per-Step WHO Classification — Skill: classify_imci_step
    # -------------------------------------------------------------------

    def _classify_completed_step(self, step: str) -> dict[str, Any] | None:
        """Run deterministic WHO IMCI classification for a completed step.

        This is the medical safety boundary — classification is CODE, not LLM.
        """
        from malaika.imci_protocol import (
            classify_breathing,
            classify_danger_signs,
            classify_diarrhea,
            classify_fever,
            classify_nutrition,
        )

        if step == "danger_signs":
            ds = classify_danger_signs(
                lethargic=self.findings["lethargic"],
                unconscious=self.findings["unconscious"],
                unable_to_drink=self.findings["unable_to_drink"],
                vomits_everything=self.findings["vomits_everything"],
            )
            if ds:
                self.belief.update_severity(ds.severity.value)
                return {
                    "type": "classification",
                    "step": "danger_signs",
                    "severity": ds.severity.value,
                    "label": ds.classification.value.replace("_", " ").title(),
                    "reasoning": ds.reasoning,
                }
            return {
                "type": "classification",
                "step": "danger_signs",
                "severity": "green",
                "label": "No Danger Signs",
                "reasoning": "No general danger signs detected. WHO IMCI p.2.",
            }

        if step == "breathing":
            age = max(self.age_months, 2)
            br = classify_breathing(
                age_months=age,
                has_cough=self.findings["has_cough"],
                breathing_rate=self.findings["breathing_rate"],
                has_indrawing=self.findings["has_indrawing"],
                has_stridor=self.findings["has_stridor"],
                has_wheeze=self.findings["has_wheeze"],
            )
            self.belief.update_severity(br.severity.value)
            return {
                "type": "classification",
                "step": "breathing",
                "severity": br.severity.value,
                "label": br.classification.value.replace("_", " ").title(),
                "reasoning": br.reasoning,
            }

        if step == "diarrhea":
            if not self.findings["has_diarrhea"]:
                return {
                    "type": "classification",
                    "step": "diarrhea",
                    "severity": "green",
                    "label": "No Diarrhea",
                    "reasoning": "No diarrhea reported.",
                }
            dd = classify_diarrhea(
                has_diarrhea=True,
                duration_days=self.findings["diarrhea_days"],
                blood_in_stool=self.findings["blood_in_stool"],
                sunken_eyes=self.findings["sunken_eyes"],
                skin_pinch_slow=self.findings["skin_pinch_slow"],
                lethargic=self.findings["lethargic"],
            )
            if dd:
                self.belief.update_severity(dd.severity.value)
                return {
                    "type": "classification",
                    "step": "diarrhea",
                    "severity": dd.severity.value,
                    "label": dd.classification.value.replace("_", " ").title(),
                    "reasoning": dd.reasoning,
                }

        if step == "fever":
            if not self.findings["has_fever"]:
                return {
                    "type": "classification",
                    "step": "fever",
                    "severity": "green",
                    "label": "No Fever",
                    "reasoning": "No fever reported.",
                }
            fv = classify_fever(
                has_fever=True,
                duration_days=self.findings["fever_days"],
                stiff_neck=self.findings["stiff_neck"],
                malaria_risk=self.findings["malaria_risk"],
            )
            if fv:
                self.belief.update_severity(fv.severity.value)
                return {
                    "type": "classification",
                    "step": "fever",
                    "severity": fv.severity.value,
                    "label": fv.classification.value.replace("_", " ").title(),
                    "reasoning": fv.reasoning,
                }

        if step == "nutrition":
            nt = classify_nutrition(
                visible_wasting=self.findings["visible_wasting"],
                edema=self.findings["edema"],
                muac_mm=self.findings["muac_mm"],
            )
            self.belief.update_severity(nt.severity.value)
            return {
                "type": "classification",
                "step": "nutrition",
                "severity": nt.severity.value,
                "label": nt.classification.value.replace("_", " ").title(),
                "reasoning": nt.reasoning,
            }

        return None

    # -------------------------------------------------------------------
    # Assessment Complete
    # -------------------------------------------------------------------

    def _emit_assessment_complete(self, events: list[dict[str, Any]]) -> None:
        """Emit the final assessment summary with all classifications."""
        # Collect all step classifications
        classifications: list[dict[str, Any]] = []
        for step in CLINICAL_STEPS:
            cls_event = self._classify_completed_step(step)
            if cls_event:
                classifications.append({
                    "domain": cls_event["step"].replace("_", " ").title(),
                    "classification": cls_event["label"],
                    "severity": cls_event["severity"],
                    "reasoning": cls_event["reasoning"],
                })

        severity = self.belief.current_severity
        urgency_map = {
            "red": "URGENT: Go to a health facility IMMEDIATELY",
            "yellow": "See a health worker within 24 hours",
            "green": "Treat at home with follow-up in 5 days",
        }

        events.append({
            "type": "assessment_complete",
            "severity": severity,
            "urgency": urgency_map.get(severity, "Consult a health worker"),
            "classifications": classifications,
            "age_months": self.age_months,
        })

        # Check for danger alert
        if severity == "red":
            danger_signs = [
                k for k in ["lethargic", "unconscious", "unable_to_drink",
                            "vomits_everything", "has_convulsions"]
                if self.findings.get(k)
            ]
            if danger_signs:
                events.append({
                    "type": "danger_alert",
                    "message": "URGENT REFERRAL NEEDED. General danger sign detected. This child needs immediate care.",
                    "signs": danger_signs,
                })

    # -------------------------------------------------------------------
    # Image Request
    # -------------------------------------------------------------------

    def _maybe_request_image(self, events: list[dict[str, Any]]) -> None:
        """Emit image request if the current step benefits from a photo."""
        if self._image_received_this_step:
            return
        if self.step not in IMAGE_REQUEST_PROMPTS:
            return
        # Only request on the first message of the step
        msgs_in_step = self._count_user_msgs_since_step_start()
        if msgs_in_step != 1:
            return

        req = IMAGE_REQUEST_PROMPTS[self.step]
        events.append({
            "type": "image_request",
            "step": self.step,
            "skill": req["skill"],
            "prompt": req["prompt"],
        })

    # -------------------------------------------------------------------
    # Classification Context (for final LLM presentation)
    # -------------------------------------------------------------------

    def _build_classification_context(self) -> str:
        """Build the classification report with reasoning for Gemma 4 to present."""
        from malaika.imci_protocol import (
            classify_breathing,
            classify_danger_signs,
            classify_diarrhea,
            classify_fever,
            classify_nutrition,
        )

        results: list[dict[str, Any]] = []

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

        age = max(self.age_months, 2)
        br = classify_breathing(
            age_months=age,
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

        if self.findings["has_diarrhea"]:
            dd = classify_diarrhea(
                has_diarrhea=True,
                duration_days=self.findings["diarrhea_days"],
                blood_in_stool=self.findings["blood_in_stool"],
                sunken_eyes=self.findings["sunken_eyes"],
                skin_pinch_slow=self.findings["skin_pinch_slow"],
                lethargic=self.findings["lethargic"],
            )
            if dd:
                results.append({
                    "domain": "Diarrhea",
                    "classification": dd.classification.value,
                    "severity": dd.severity.value,
                    "reasoning": self._diarrhea_reasoning(),
                })

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
            "1. Overall severity (use the word: GREEN, YELLOW, or RED)\n"
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

    @staticmethod
    def _extract_age(text: str) -> int | None:
        """Extract age in months from text, handling both digits and word numbers."""
        _WORD_NUMBERS: dict[str, int] = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
            "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
            "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
            "nineteen": 19, "twenty": 20, "twenty-one": 21, "twenty-two": 22,
            "twenty-three": 23, "twenty-four": 24, "thirty": 30, "thirty-six": 36,
            "forty": 40, "forty-eight": 48, "fifty": 50,
        }
        text_lower = text.lower()
        # Try digit match first
        match = re.search(r'\b(\d+)\b', text_lower)
        if match:
            return int(match.group(1))
        # Try word number match (with word boundaries)
        for word, val in sorted(_WORD_NUMBERS.items(), key=lambda x: -len(x[0])):
            if re.search(r'\b' + re.escape(word) + r'\b', text_lower):
                return val
        return None

    def _fallback_response(self) -> str:
        """Generate a basic response when the model is not available."""
        if self.step == "greeting":
            return "Hello, I am Malaika. How old is your child in months?"
        return "I am having trouble processing right now. Please try again."

    def _count_user_msgs_since_step_start(self) -> int:
        """Count user messages since the current step started."""
        count = 0
        for msg in self.conversation_history[self._step_start_msg_count:]:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if content and not content.startswith("["):
                    count += 1
        return count

    def reset(self) -> None:
        """Reset the session for a new assessment."""
        self.step = "greeting"
        self.age_months = 0
        self.conversation_history.clear()
        self.observations.clear()
        self._fields_answered.clear()
        self._image_received_this_step = False
        self._step_start_msg_count = 0
        self._pending_question_topic = None
        self.belief = BeliefState()
        self.findings = {
            k: (False if isinstance(v, bool) else (0 if isinstance(v, int) else None))
            for k, v in self.findings.items()
        }
        logger.info("session_reset")
