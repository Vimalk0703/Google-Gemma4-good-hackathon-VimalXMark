"""Treatment plan generation prompts — IMCI treatment instructions.

Covers: generating step-by-step treatment instructions for caregivers
based on the IMCI classification results. Uses higher temperature (0.3)
for natural-sounding caregiver-friendly language.
"""

from malaika.prompts.base import PromptTemplate
from malaika.prompts import PromptRegistry
from malaika.prompts.system import SYSTEM_TREATMENT_ADVISOR


# --- Treatment Plan Generation ---
GENERATE_PLAN = PromptRegistry.register(PromptTemplate(
    name="treatment.generate_plan",
    version="1.0.0",
    description=(
        "Generate clear, step-by-step treatment instructions for a caregiver "
        "based on IMCI classification results and the child's condition."
    ),
    system_prompt=SYSTEM_TREATMENT_ADVISOR,
    user_template=(
        "A child has been assessed using the WHO IMCI protocol.\n\n"
        "Child's age: {child_age_months} months\n"
        "IMCI classifications: {classifications}\n"
        "Urgency level: {urgency}\n"
        "Language preference: {language}\n\n"
        "Generate clear treatment instructions for the caregiver. Follow these rules:\n\n"
        "1. If urgency is URGENT REFERRAL:\n"
        "   - Give pre-referral treatments first (e.g., first dose of antibiotic)\n"
        "   - Clearly state the child MUST go to a health facility immediately\n"
        "   - Explain danger signs to watch for during travel\n\n"
        "2. If urgency is TREAT AT HOME:\n"
        "   - Give step-by-step medication instructions (drug, dose, frequency, duration)\n"
        "   - Explain how to give ORS if dehydration is present\n"
        "   - List feeding advice appropriate for the child's age\n"
        "   - State when to return immediately (danger signs)\n"
        "   - State when to return for follow-up\n\n"
        "3. Always:\n"
        "   - Use simple, non-medical language\n"
        "   - Number each step\n"
        "   - Specify exact quantities (e.g., 'half a tablet', '5 ml')\n"
        "   - Include when to seek emergency care\n\n"
        "Write the instructions in {language}."
    ),
    required_variables=frozenset({
        "child_age_months",
        "classifications",
        "urgency",
        "language",
    }),
    expected_output_format="text",
    output_schema=None,
    max_tokens=500,
    temperature=0.3,
))
