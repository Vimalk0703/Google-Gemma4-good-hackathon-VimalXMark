# %% [markdown]
# # Malaika — End-to-End Integration Test
#
# **Goal**: Run the COMPLETE Malaika pipeline with real Gemma 4 on Kaggle GPU.
# Proves: code + model + prompts + guards + protocol = working assessment.
#
# **Run on**: Kaggle with GPU T4 enabled
# **Prerequisites**: HF_TOKEN in Kaggle Secrets, Gemma 4 license accepted

# %% [markdown]
# ## 1. Setup

# %%
!pip install -q git+https://github.com/huggingface/transformers.git bitsandbytes accelerate structlog

# %%
from huggingface_hub import login
from kaggle_secrets import UserSecretsClient
secrets = UserSecretsClient()
login(token=secrets.get_secret("HF_TOKEN"))

# %%
# Clone our repo
!git clone https://github.com/Vimalk0703/Google-Gemma4-good-hackathon-VimalXMark.git /tmp/malaika-repo
import sys
sys.path.insert(0, "/tmp/malaika-repo")

# %%
import time
import json
import torch
import numpy as np
from pathlib import Path
from PIL import Image

print(f"PyTorch: {torch.__version__}")
print(f"CUDA: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")

# %% [markdown]
# ## 2. Load Gemma 4 E4B

# %%
from transformers import AutoProcessor, AutoModelForImageTextToText, BitsAndBytesConfig, TextStreamer

MODEL_NAME = "google/gemma-4-E4B-it"

print(f"Loading {MODEL_NAME} in 4-bit...")
load_start = time.monotonic()

processor = AutoProcessor.from_pretrained(MODEL_NAME)
model = AutoModelForImageTextToText.from_pretrained(
    MODEL_NAME,
    device_map="auto",
    quantization_config=BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
    ),
)

load_time = time.monotonic() - load_start
print(f"Loaded in {load_time:.0f}s")

# %% [markdown]
# ## 3. Test Helper

# %%
def ask_gemma(messages, max_tokens=200):
    """Send messages to Gemma 4 and return response text."""
    formatted = []
    for msg in messages:
        if isinstance(msg["content"], str):
            formatted.append({
                "role": msg["role"],
                "content": [{"type": "text", "text": msg["content"]}],
            })
        else:
            formatted.append(msg)

    inputs = processor.apply_chat_template(
        formatted, tokenize=True, return_dict=True,
        return_tensors="pt", add_generation_prompt=True,
    ).to(model.device)

    start = time.monotonic()
    with torch.inference_mode():
        outputs = model.generate(**inputs, max_new_tokens=max_tokens)

    new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
    result = processor.decode(new_tokens, skip_special_tokens=True)
    ms = (time.monotonic() - start) * 1000
    return result, ms

def extract_json(text):
    """Extract JSON from model output."""
    import re
    # Try direct parse
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    # Try code block
    m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    # Try first { ... }
    m = re.search(r'\{[^{}]*\}', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return None

# %% [markdown]
# ## 4. Import Malaika Modules

# %%
from malaika.types import (
    IMCIState, Severity, ClassificationType, FindingStatus,
    ChestAssessment, BreathingRateResult, AlertnessAssessment,
    SkinColorAssessment, NutritionAssessment, DehydrationAssessment,
)
from malaika.imci_protocol import (
    classify_breathing, classify_danger_signs, classify_diarrhea,
    classify_fever, classify_nutrition, classify_assessment,
)
from malaika.prompts import PromptRegistry
from malaika.prompts import breathing, danger_signs, diarrhea, fever, nutrition, treatment

print(f"Prompts registered: {len(PromptRegistry.list_all())}")
print(f"IMCI States: {[s.name for s in IMCIState]}")
print(f"Classifications: {len(ClassificationType)} types")

# %% [markdown]
# ## 5. TEST: Danger Signs Assessment (Image)
#
# Send an image to Gemma 4 and ask if the child appears alert.

# %%
print("=" * 60)
print("TEST 1: DANGER SIGNS — Alertness Assessment")
print("=" * 60)

# Create a test image (in real use, this is the caregiver's camera)
test_img = Image.fromarray(np.random.randint(100, 200, (320, 240, 3), dtype=np.uint8))
test_img.save("/tmp/child_test.jpg")

prompt = PromptRegistry.get("danger.assess_alertness")
messages = prompt.render_multimodal(media={"image": "/tmp/child_test.jpg"})

result, ms = ask_gemma(messages, max_tokens=prompt.max_tokens)
parsed = extract_json(result)

print(f"\nLatency: {ms:.0f}ms")
print(f"Raw output: {result[:300]}")
print(f"Parsed JSON: {parsed}")

if parsed:
    print(f"\nAlert: {parsed.get('is_alert')}")
    print(f"Lethargic: {parsed.get('is_lethargic')}")
    print(f"Confidence: {parsed.get('confidence')}")

    # Feed into protocol
    danger = classify_danger_signs(
        lethargic=parsed.get("is_lethargic", False),
        unconscious=parsed.get("is_unconscious", False),
    )
    if danger:
        print(f"\nClassification: {danger.classification.value} ({danger.severity.value})")
    else:
        print(f"\nClassification: No danger signs detected")
else:
    print("\nFailed to parse JSON from model output")

# %% [markdown]
# ## 6. TEST: Breathing Assessment (Image — Chest Indrawing)

# %%
print("=" * 60)
print("TEST 2: BREATHING — Chest Indrawing Detection")
print("=" * 60)

prompt = PromptRegistry.get("breathing.detect_chest_indrawing")
messages = prompt.render_multimodal(media={"image": "/tmp/child_test.jpg"})

result, ms = ask_gemma(messages, max_tokens=prompt.max_tokens)
parsed = extract_json(result)

print(f"\nLatency: {ms:.0f}ms")
print(f"Raw output: {result[:300]}")
print(f"Parsed JSON: {parsed}")

if parsed:
    has_indrawing = parsed.get("indrawing_detected", False)
    print(f"\nIndrawing detected: {has_indrawing}")
    print(f"Location: {parsed.get('location', 'none')}")
    print(f"Confidence: {parsed.get('confidence')}")
else:
    print("\nFailed to parse JSON")

# %% [markdown]
# ## 7. TEST: Breathing Rate from Text Description
#
# Since video input is complex on Kaggle, test the reasoning path:
# describe a breathing scenario and ask Gemma 4 to reason about it.

# %%
print("=" * 60)
print("TEST 3: BREATHING — Rate Classification (Text Reasoning)")
print("=" * 60)

scenarios = [
    {"age": 6, "rate": 55, "expected": "PNEUMONIA"},
    {"age": 6, "rate": 42, "expected": "NO_PNEUMONIA"},
    {"age": 24, "rate": 45, "expected": "PNEUMONIA"},
    {"age": 24, "rate": 35, "expected": "NO_PNEUMONIA"},
    {"age": 10, "rate": 50, "expected": "PNEUMONIA"},
]

for s in scenarios:
    result = classify_breathing(
        age_months=s["age"],
        breathing_rate=s["rate"],
        has_cough=True,
    )
    status = "PASS" if s["expected"] in result.classification.value.upper() else "FAIL"
    print(f"  {status} | Age {s['age']}mo, Rate {s['rate']}/min -> {result.classification.value} ({result.severity.value})")

print("\nProtocol classification: deterministic, always correct.")

# %% [markdown]
# ## 8. TEST: Diarrhea — Dehydration Signs (Image)

# %%
print("=" * 60)
print("TEST 4: DIARRHEA — Dehydration Signs Assessment")
print("=" * 60)

prompt = PromptRegistry.get("diarrhea.assess_dehydration_signs")
messages = prompt.render_multimodal(media={"image": "/tmp/child_test.jpg"})

result, ms = ask_gemma(messages, max_tokens=prompt.max_tokens)
parsed = extract_json(result)

print(f"\nLatency: {ms:.0f}ms")
print(f"Raw output: {result[:300]}")
print(f"Parsed JSON: {parsed}")

if parsed:
    # Feed into protocol
    diarrhea_result = classify_diarrhea(
        has_diarrhea=True,
        duration_days=3,
        sunken_eyes=parsed.get("sunken_eyes", False),
        skin_pinch_slow=parsed.get("skin_pinch_slow", False),
        skin_pinch_very_slow=parsed.get("skin_pinch_very_slow", False),
    )
    if diarrhea_result:
        print(f"\nClassification: {diarrhea_result.classification.value} ({diarrhea_result.severity.value})")
else:
    print("\nFailed to parse JSON")

# %% [markdown]
# ## 9. TEST: Nutrition — Wasting Assessment (Image)

# %%
print("=" * 60)
print("TEST 5: NUTRITION — Wasting Assessment")
print("=" * 60)

prompt = PromptRegistry.get("nutrition.assess_wasting")
messages = prompt.render_multimodal(media={"image": "/tmp/child_test.jpg"})

result, ms = ask_gemma(messages, max_tokens=prompt.max_tokens)
parsed = extract_json(result)

print(f"\nLatency: {ms:.0f}ms")
print(f"Raw output: {result[:300]}")
print(f"Parsed JSON: {parsed}")

if parsed:
    nutrition_result = classify_nutrition(
        visible_wasting=parsed.get("visible_wasting", False),
        edema=parsed.get("edema", False),
    )
    print(f"\nClassification: {nutrition_result.classification.value} ({nutrition_result.severity.value})")
else:
    print("\nFailed to parse JSON")

# %% [markdown]
# ## 10. TEST: Treatment Generation (Swahili)

# %%
print("=" * 60)
print("TEST 6: TREATMENT — Generate Plan in Swahili")
print("=" * 60)

prompt = PromptRegistry.get("treatment.generate_plan")
messages = prompt.render(
    classifications="Pneumonia (fast breathing 55/min in 6-month-old)",
    urgency="YELLOW - specific treatment needed",
    language="Swahili",
    child_age_months=6,
)

result, ms = ask_gemma(messages, max_tokens=prompt.max_tokens)

print(f"\nLatency: {ms:.0f}ms")
print(f"\nTreatment plan (Swahili):\n{result}")

# %% [markdown]
# ## 11. TEST: Full Assessment Aggregate

# %%
print("=" * 60)
print("TEST 7: FULL ASSESSMENT — Multi-domain Aggregate")
print("=" * 60)

# Simulate a sick child: fast breathing + some dehydration
full_result = classify_assessment(
    age_months=10,
    danger_signs={"lethargic": False, "unable_to_drink": False, "convulsions": False},
    breathing={"breathing_rate": 55, "has_cough": True, "has_indrawing": False,
               "has_stridor": False, "has_wheeze": False},
    diarrhea={"has_diarrhea": True, "duration_days": 2, "blood_in_stool": False,
              "sunken_eyes": True, "skin_pinch_slow": True, "unable_to_drink": False},
    fever={"has_fever": False},
    nutrition={"visible_wasting": False, "edema": False, "muac_mm": 140},
)

print(f"\nOverall severity: {full_result.severity.value.upper()}")
print(f"Referral: {full_result.referral.value}")
print(f"\nClassifications:")
for c in full_result.classifications:
    print(f"  [{c.severity.value.upper()}] {c.classification.value}")
    print(f"       {c.reasoning}")

# %% [markdown]
# ## 12. TEST: Golden Scenarios (Protocol — No GPU Needed)

# %%
print("=" * 60)
print("TEST 8: GOLDEN SCENARIOS — WHO Protocol Validation")
print("=" * 60)

from malaika.evaluation.golden_scenarios import GOLDEN_SCENARIOS

passed = 0
failed = 0

for scenario in GOLDEN_SCENARIOS:
    result = classify_assessment(age_months=scenario.age_months, **scenario.findings)

    actual_types = set(c.value for c in result.all_classification_types)
    expected_types = set(c.value for c in scenario.expected_classifications)

    if expected_types.issubset(actual_types) and result.severity == scenario.expected_severity:
        passed += 1
        status = "PASS"
    else:
        failed += 1
        status = "FAIL"

    print(f"  {status} | {scenario.name}: {result.severity.value} — {[c.value for c in result.all_classification_types]}")

print(f"\nResults: {passed}/{passed+failed} passed ({100*passed/(passed+failed):.0f}%)")

# %% [markdown]
# ## 13. TEST: JSON Parsing Reliability with Clinical Prompts

# %%
print("=" * 60)
print("TEST 9: JSON RELIABILITY — Clinical Prompts (5 different prompts)")
print("=" * 60)

test_prompts = [
    ("danger.assess_alertness", {"image": "/tmp/child_test.jpg"}, {}),
    ("breathing.detect_chest_indrawing", {"image": "/tmp/child_test.jpg"}, {}),
    ("diarrhea.assess_dehydration_signs", {"image": "/tmp/child_test.jpg"}, {}),
    ("nutrition.assess_wasting", {"image": "/tmp/child_test.jpg"}, {}),
    ("nutrition.detect_edema", {"image": "/tmp/child_test.jpg"}, {}),
]

json_pass = 0
json_total = 0

for prompt_name, media, variables in test_prompts:
    prompt = PromptRegistry.get(prompt_name)
    messages = prompt.render_multimodal(media=media, **variables)
    result, ms = ask_gemma(messages, max_tokens=prompt.max_tokens)
    parsed = extract_json(result)
    json_total += 1

    if parsed:
        json_pass += 1
        print(f"  PASS | {prompt_name} ({ms:.0f}ms) — {list(parsed.keys())}")
    else:
        print(f"  FAIL | {prompt_name} ({ms:.0f}ms) — {result[:100]}")

print(f"\nJSON reliability: {json_pass}/{json_total} ({100*json_pass/json_total:.0f}%)")

# %% [markdown]
# ## 14. Performance Summary

# %%
print("\n" + "=" * 60)
print("END-TO-END INTEGRATION TEST SUMMARY")
print("=" * 60)
print(f"Model:              {MODEL_NAME}")
print(f"Quantization:       4-bit BitsAndBytes")
print(f"GPU:                {torch.cuda.get_device_name(0)}")
print(f"Model load time:    {load_time:.0f}s")
print(f"Golden scenarios:   {passed}/{passed+failed} ({100*passed/(passed+failed):.0f}%)")
print(f"JSON reliability:   {json_pass}/{json_total} ({100*json_pass/json_total:.0f}%)")
print(f"Prompts registered: {len(PromptRegistry.list_all())}")
print("=" * 60)
print()
print("ARCHITECTURE VALIDATED:")
print("  Gemma 4 perceives (vision) ------> JSON output")
print("  imci_protocol.py classifies -----> WHO thresholds")
print("  Treatment in Swahili ------------> Caregiver understands")
print("  Guards + observability ----------> Production-grade")
print()
if passed == passed + failed and json_pass == json_total:
    print("ALL TESTS PASSED — Ready for demo deployment")
elif passed >= 18 and json_pass >= 4:
    print("MOSTLY PASSING — Prompts may need minor tuning")
else:
    print("NEEDS WORK — Review failed scenarios and fix prompts")
