"""Malaika Skills Registry — Clinical skill definitions for the IMCI agent.

Each skill is a structured tool that Gemma 4 can reason about and invoke
during the IMCI assessment. Skills provide:
- Typed input/output contracts
- Human-readable descriptions for the LLM context
- Mapping to IMCI protocol steps
- Execution results with confidence and followup suggestions

Architecture:
    - Skills define WHAT can be done (declarative)
    - ChatEngine decides WHEN to invoke each skill (agentic reasoning)
    - imci_protocol.py decides WHAT the findings mean (deterministic classification)
    - Gemma 4 does the actual perception work (vision, audio, speech)

This module MUST NOT contain inference logic or model calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Skill Definition
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Skill:
    """A clinical assessment skill that the IMCI agent can invoke.

    Each skill maps to a specific perception or reasoning capability
    backed by Gemma 4. Skills are organized by IMCI protocol step.

    Attributes:
        name: Unique skill identifier (e.g. "assess_alertness").
        description: What this skill does (shown to Gemma 4 for reasoning).
        imci_step: Which IMCI step this skill belongs to ("danger_signs", etc.).
        input_type: Primary input modality ("image", "audio", "text", "video", "findings").
        parameters: Parameter name → description mapping.
        returns: Return field name → description mapping.
        requires_media: Whether this skill needs camera/mic input from caregiver.
        media_prompt: What to tell the caregiver if media is needed.
    """

    name: str
    description: str
    imci_step: str
    input_type: str
    parameters: dict[str, str]
    returns: dict[str, str]
    requires_media: bool = False
    media_prompt: str = ""


# ---------------------------------------------------------------------------
# Skill Execution Result
# ---------------------------------------------------------------------------


@dataclass
class SkillResult:
    """Result of executing a clinical skill.

    Attributes:
        skill_name: Which skill produced this result.
        success: Whether the skill executed without error.
        findings: Structured findings dict (e.g. {"lethargic": True}).
        description: Human-readable summary of what was observed.
        confidence: Confidence score 0.0-1.0.
        requires_followup: Whether the agent should ask a clarifying question.
        followup_suggestion: Suggested followup if needed.
    """

    skill_name: str
    success: bool
    findings: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    confidence: float = 0.0
    requires_followup: bool = False
    followup_suggestion: str = ""


# ---------------------------------------------------------------------------
# Belief State — What the Agent Knows
# ---------------------------------------------------------------------------


@dataclass
class BeliefState:
    """Tracks what the IMCI agent knows, what's uncertain, and what's pending.

    Updated after each skill execution and caregiver response.
    Used by ChatEngine to decide what to ask/do next.

    Attributes:
        confirmed: Findings confirmed by skills or user responses.
        uncertain: Findings with low confidence — key → reason string.
        pending_questions: Questions the agent still needs to ask.
        skills_invoked: Skills already executed in the current step.
        current_severity: Running worst-case severity across all steps.
    """

    confirmed: dict[str, Any] = field(default_factory=dict)
    uncertain: dict[str, str] = field(default_factory=dict)
    pending_questions: list[str] = field(default_factory=list)
    skills_invoked: list[str] = field(default_factory=list)
    current_severity: str = "green"

    def update_severity(self, severity: str) -> None:
        """Update running severity — only escalates, never de-escalates."""
        order = {"green": 0, "yellow": 1, "red": 2}
        if order.get(severity, 0) > order.get(self.current_severity, 0):
            self.current_severity = severity

    def reset_for_step(self) -> None:
        """Reset per-step tracking when advancing to a new IMCI step."""
        self.skills_invoked.clear()
        self.pending_questions.clear()

    def mark_skill_invoked(self, skill_name: str) -> None:
        """Record that a skill has been executed this step."""
        if skill_name not in self.skills_invoked:
            self.skills_invoked.append(skill_name)

    def confirm_finding(self, key: str, value: Any) -> None:
        """Confirm a clinical finding."""
        self.confirmed[key] = value
        self.uncertain.pop(key, None)

    def mark_uncertain(self, key: str, reason: str) -> None:
        """Mark a finding as uncertain with a reason."""
        if key not in self.confirmed:
            self.uncertain[key] = reason


# ---------------------------------------------------------------------------
# Skill Registry
# ---------------------------------------------------------------------------


class SkillRegistry:
    """Central registry for all clinical skills.

    Skills are registered at module import time. The registry provides
    lookup by name, by IMCI step, and formatted tool descriptions for
    injecting into Gemma 4's system prompt.
    """

    _skills: dict[str, Skill] = {}

    @classmethod
    def register(cls, skill: Skill) -> Skill:
        """Register a skill. Returns the skill for assignment."""
        cls._skills[skill.name] = skill
        return skill

    @classmethod
    def get(cls, name: str) -> Skill:
        """Get a skill by name. Raises KeyError if not found."""
        return cls._skills[name]

    @classmethod
    def for_step(cls, step: str) -> list[Skill]:
        """Get all skills for a given IMCI step."""
        return [s for s in cls._skills.values() if s.imci_step == step]

    @classmethod
    def list_all(cls) -> list[Skill]:
        """Get all registered skills."""
        return list(cls._skills.values())

    @classmethod
    def media_skills_for_step(cls, step: str) -> list[Skill]:
        """Get skills that require media input for a given step."""
        return [s for s in cls.for_step(step) if s.requires_media]

    @classmethod
    def as_tool_descriptions(cls, step: str) -> str:
        """Format skills as tool descriptions for Gemma 4 context.

        Produces a structured text block that tells Gemma 4 what tools
        are available for the current IMCI step.

        Args:
            step: Current IMCI step name.

        Returns:
            Formatted string describing available skills.
        """
        skills = cls.for_step(step)
        # Also include universal skills
        skills.extend(s for s in cls._skills.values() if s.imci_step == "any" and s not in skills)

        if not skills:
            return "No specialized skills available for this step."

        lines: list[str] = ["Available clinical skills for this step:"]
        for s in skills:
            params = ", ".join(f"{k}: {v}" for k, v in s.parameters.items())
            returns = ", ".join(f"{k}: {v}" for k, v in s.returns.items())
            media_note = f" [Requires: {s.input_type}]" if s.requires_media else ""
            lines.append(f"  - {s.name}: {s.description}{media_note}")
            if params:
                lines.append(f"    Input: {params}")
            if returns:
                lines.append(f"    Output: {returns}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Skill Definitions — All 12 Clinical Skills
# ---------------------------------------------------------------------------

# === DANGER SIGNS SKILLS ===

ASSESS_ALERTNESS = SkillRegistry.register(
    Skill(
        name="assess_alertness",
        description="Analyze a photo of the child to assess alertness level (alert, lethargic, or unconscious)",
        imci_step="danger_signs",
        input_type="image",
        parameters={"image": "Photo of the child's face and upper body"},
        returns={
            "alert": "Child is awake and responsive (bool)",
            "lethargic": "Child is abnormally sleepy, difficult to wake (bool)",
            "unconscious": "Child cannot be woken (bool)",
        },
        requires_media=True,
        media_prompt="Can you hold the phone so I can see your child? I want to check how alert they are.",
    )
)

ASSESS_SKIN_COLOR = SkillRegistry.register(
    Skill(
        name="assess_skin_color",
        description="Analyze skin color from a photo to detect jaundice, cyanosis, or pallor",
        imci_step="danger_signs",
        input_type="image",
        parameters={"image": "Photo showing the child's skin"},
        returns={
            "jaundice": "Yellowish skin/eyes suggesting liver issues (bool)",
            "cyanosis": "Bluish skin suggesting low oxygen (bool)",
            "pallor": "Pale skin suggesting anemia (bool)",
        },
        requires_media=True,
        media_prompt="I'd like to look at your child's skin color. Can you show me their face in good light?",
    )
)

PARSE_CAREGIVER_RESPONSE = SkillRegistry.register(
    Skill(
        name="parse_caregiver_response",
        description="Extract clinical facts from the caregiver's spoken or typed response",
        imci_step="any",
        input_type="text",
        parameters={"text": "Caregiver's response (transcribed speech or typed)"},
        returns={
            "intent": "What the caregiver is communicating (affirmative/negative/informative/uncertain)",
            "entities": "Clinical entities mentioned (symptoms, duration, severity)",
            "findings": "Extracted IMCI-relevant findings",
        },
        requires_media=False,
    )
)

# === BREATHING SKILLS ===

DETECT_CHEST_INDRAWING = SkillRegistry.register(
    Skill(
        name="detect_chest_indrawing",
        description="Analyze a chest photo to detect subcostal or intercostal chest indrawing (WHO danger sign)",
        imci_step="breathing",
        input_type="image",
        parameters={"image": "Photo of the child's chest area"},
        returns={
            "indrawing_detected": "Lower chest pulls inward when breathing (bool)",
            "description": "What was observed in the image",
        },
        requires_media=True,
        media_prompt="Can you take a photo of your child's chest area? I want to check how they are breathing.",
    )
)

COUNT_BREATHING_RATE = SkillRegistry.register(
    Skill(
        name="count_breathing_rate",
        description="Count breathing rate from a 15-second video of the child's chest",
        imci_step="breathing",
        input_type="video",
        parameters={"video": "15-second video of chest wall movement"},
        returns={
            "rate_per_minute": "Breaths per minute (int)",
            "is_fast": "Whether rate exceeds WHO threshold for age (bool)",
        },
        requires_media=True,
        media_prompt="Can you record a short video of your child's chest for about 15 seconds? I need to count their breathing.",
    )
)

CLASSIFY_BREATH_SOUNDS = SkillRegistry.register(
    Skill(
        name="classify_breath_sounds",
        description="Classify breath sounds from audio or spectrogram to detect wheeze, stridor, or grunting",
        imci_step="breathing",
        input_type="audio",
        parameters={"audio": "Recording of the child's breathing sounds"},
        returns={
            "wheeze": "Whistling sound during breathing (bool)",
            "stridor": "Harsh high-pitched sound when calm (bool)",
            "grunting": "Short grunting noise with each breath (bool)",
            "crackles": "Crackling/bubbling sound (bool)",
        },
        requires_media=True,
        media_prompt="Can you hold the phone near your child's chest so I can listen to their breathing?",
    )
)

# === DIARRHEA SKILLS ===

ASSESS_DEHYDRATION_SIGNS = SkillRegistry.register(
    Skill(
        name="assess_dehydration_signs",
        description="Analyze a photo of the child's face to detect dehydration signs (sunken eyes, dry appearance)",
        imci_step="diarrhea",
        input_type="image",
        parameters={"image": "Photo of the child's face"},
        returns={
            "sunken_eyes": "Eyes appear sunken or deeper than normal (bool)",
            "dry_appearance": "Child's skin or mouth appears dry (bool)",
            "description": "What was observed",
        },
        requires_media=True,
        media_prompt="Can you take a close photo of your child's face? I want to check for signs of dehydration.",
    )
)

# === NUTRITION SKILLS ===

ASSESS_WASTING = SkillRegistry.register(
    Skill(
        name="assess_wasting",
        description="Analyze a photo to detect visible severe wasting (very thin, ribs/bones showing)",
        imci_step="nutrition",
        input_type="image",
        parameters={"image": "Photo showing the child's body"},
        returns={
            "visible_wasting": "Severe visible wasting observed (bool)",
            "description": "What was observed",
        },
        requires_media=True,
        media_prompt="Can you take a photo showing your child's body? I want to check their nutrition.",
    )
)

DETECT_EDEMA = SkillRegistry.register(
    Skill(
        name="detect_edema",
        description="Analyze a photo to detect bilateral pitting edema of the feet",
        imci_step="nutrition",
        input_type="image",
        parameters={"image": "Photo of the child's feet"},
        returns={
            "edema_detected": "Swelling in both feet (bool)",
            "description": "What was observed",
        },
        requires_media=True,
        media_prompt="Can you show me your child's feet? I want to check for any swelling.",
    )
)

# === CLINICAL SKILLS (deterministic — run by code, not LLM) ===

CLASSIFY_IMCI_STEP = SkillRegistry.register(
    Skill(
        name="classify_imci_step",
        description="Run WHO IMCI deterministic classification for the completed assessment step",
        imci_step="any",
        input_type="findings",
        parameters={"step": "IMCI step name", "findings": "Collected clinical findings"},
        returns={
            "classification": "WHO IMCI classification label",
            "severity": "RED, YELLOW, or GREEN",
            "reasoning": "Why this classification was assigned with WHO page reference",
        },
        requires_media=False,
    )
)

GENERATE_TREATMENT = SkillRegistry.register(
    Skill(
        name="generate_treatment",
        description="Generate a step-by-step treatment plan based on WHO IMCI classifications",
        imci_step="treatment",
        input_type="findings",
        parameters={
            "classifications": "All IMCI classifications from assessment",
            "age_months": "Child's age in months",
            "language": "Language for instructions",
        },
        returns={
            "treatment_plan": "Step-by-step caregiver instructions",
            "urgency": "How urgently to seek care",
            "follow_up": "When to return for checkup",
        },
        requires_media=False,
    )
)

SPEAK_TO_CAREGIVER = SkillRegistry.register(
    Skill(
        name="speak_to_caregiver",
        description="Generate an empathetic, culturally sensitive voice response for the caregiver",
        imci_step="any",
        input_type="text",
        parameters={"context": "Current assessment context and what to communicate"},
        returns={"response": "Natural language response for the caregiver"},
        requires_media=False,
    )
)
