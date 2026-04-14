# %% [markdown]
# # Malaika — Day 4: Real Data Testing + Spectrogram Pipeline Validation
#
# **Goals**:
# 1. Re-verify all Session 1 tests with prompt fixes (Tests 1 & 5)
# 2. Test breath sound classification on REAL ICBHI data via spectrograms
# 3. Verify treatment prompt fix (Swahili should output plain text, not JSON)
# 4. Benchmark spectrogram generation + vision pipeline latency
#
# **Works on**: Google Colab (T4 GPU) or Kaggle (T4 GPU)
# **ICBHI dataset**: Downloaded automatically via Kaggle API

# %% [markdown]
# ## 1. Setup

# %%
!pip install -q git+https://github.com/huggingface/transformers.git structlog librosa Pillow soundfile kaggle bitsandbytes accelerate

# %%
# Authenticate — works on both Colab and Kaggle
from huggingface_hub import login
import os

try:
    from kaggle_secrets import UserSecretsClient
    secrets = UserSecretsClient()
    login(token=secrets.get_secret("HF_TOKEN"))
    KAGGLE_USERNAME = secrets.get_secret("KAGGLE_USERNAME")
    KAGGLE_KEY = secrets.get_secret("KAGGLE_KEY")
    ENV = "kaggle"
    print("Authenticated via Kaggle secrets")
except ModuleNotFoundError:
    try:
        from google.colab import userdata
        login(token=userdata.get("HF_TOKEN"))
        KAGGLE_USERNAME = userdata.get("KAGGLE_USERNAME")
        KAGGLE_KEY = userdata.get("KAGGLE_KEY")
        ENV = "colab"
        print("Authenticated via Colab secrets")
    except Exception:
        login()
        KAGGLE_USERNAME = os.environ.get("KAGGLE_USERNAME", "")
        KAGGLE_KEY = os.environ.get("KAGGLE_KEY", "")
        ENV = "manual"
        print("Authenticated via manual login")

# Set up Kaggle API credentials for dataset download
os.makedirs(os.path.expanduser("~/.kaggle"), exist_ok=True)
with open(os.path.expanduser("~/.kaggle/kaggle.json"), "w") as f:
    import json as _json
    _json.dump({"username": KAGGLE_USERNAME, "key": KAGGLE_KEY}, f)
os.chmod(os.path.expanduser("~/.kaggle/kaggle.json"), 0o600)
print(f"Environment: {ENV}")

# %%
# Clone the repo
import subprocess, sys
REPO_DIR = "/tmp/malaika-repo"
if not os.path.exists(REPO_DIR):
    subprocess.run(["git", "clone", "-q",
        "https://github.com/Vimalk0703/Google-Gemma4-good-hackathon-VimalXMark.git",
        REPO_DIR], check=True)
else:
    subprocess.run(["git", "-C", REPO_DIR, "pull", "-q"], check=True)
sys.path.insert(0, REPO_DIR)

import time, json, re, torch
import numpy as np
from pathlib import Path
from PIL import Image

print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")

# %% [markdown]
# ## 2. Load Model

# %%
from transformers import AutoProcessor, AutoModelForImageTextToText, BitsAndBytesConfig

MODEL_NAME = "google/gemma-4-E4B-it"
print(f"Loading {MODEL_NAME} in 4-bit...")
t0 = time.monotonic()

processor = AutoProcessor.from_pretrained(MODEL_NAME)
model = AutoModelForImageTextToText.from_pretrained(
    MODEL_NAME, device_map="auto",
    quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16),
)
load_time = time.monotonic() - t0
print(f"Loaded in {load_time:.0f}s")

# %%
def ask(messages, max_tokens=200):
    """Send messages to Gemma 4 and return response."""
    fmt = []
    for m in messages:
        if isinstance(m["content"], str):
            fmt.append({"role": m["role"], "content": [{"type": "text", "text": m["content"]}]})
        else:
            fmt.append(m)
    inputs = processor.apply_chat_template(
        fmt, tokenize=True, return_dict=True,
        return_tensors="pt", add_generation_prompt=True,
    ).to(model.device)
    t = time.monotonic()
    with torch.inference_mode():
        out = model.generate(**inputs, max_new_tokens=max_tokens, do_sample=False)
    new = out[0][inputs["input_ids"].shape[1]:]
    result = processor.decode(new, skip_special_tokens=True)
    ms = (time.monotonic() - t) * 1000
    toks = len(new)
    print(f"  {ms:.0f}ms | {toks} tokens | {toks/(ms/1000):.1f} tok/s")
    return result


def ask_with_image(messages, images, max_tokens=200):
    """Send messages with PIL images to Gemma 4."""
    input_text = processor.apply_chat_template(messages, add_generation_prompt=True)
    inputs = processor(text=input_text, images=images, return_tensors="pt").to(model.device)
    t = time.monotonic()
    with torch.inference_mode():
        out = model.generate(**inputs, max_new_tokens=max_tokens, do_sample=False)
    new = out[0][inputs["input_ids"].shape[1]:]
    result = processor.decode(new, skip_special_tokens=True)
    ms = (time.monotonic() - t) * 1000
    toks = len(new)
    print(f"  {ms:.0f}ms | {toks} tokens | {toks/(ms/1000):.1f} tok/s")
    return result


def get_json(text):
    """Extract JSON object from model response."""
    for pattern in [r'\{[^{}]*\}', r'```(?:json)?\s*\n?(.*?)\n?```']:
        m = re.search(pattern, text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0) if '{' in m.group(0) else m.group(1))
            except Exception:
                pass
    return None

# %%
# Load Malaika prompts and protocol
from malaika.prompts import PromptRegistry
from malaika.prompts import breathing, danger_signs, diarrhea, fever, nutrition, treatment
from malaika.imci_protocol import (
    classify_breathing, classify_danger_signs, classify_diarrhea,
    classify_nutrition, classify_assessment,
)

# Create test image
img = Image.fromarray(np.random.randint(100, 200, (320, 240, 3), dtype=np.uint8))
img.save("/tmp/test.jpg")

print(f"Prompts registered: {len(PromptRegistry.list_all())}")

# %% [markdown]
# ## 3. Re-Verify Session 1 Tests (with prompt fixes)
#
# Tests 1 and 5 returned None in Session 1 due to thinking mode.
# The prompt fix (suppress thinking) was applied but these tests were never re-run.

# %%
print("=" * 60)
print("SECTION A: RE-VERIFY SESSION 1 TESTS")
print("=" * 60)

results = {}

# %%
print("\nTEST 1 [RE-RUN]: DANGER SIGNS — Alertness Assessment")
p = PromptRegistry.get("danger.assess_alertness")
r = ask(p.render_multimodal(media={"image": "/tmp/test.jpg"}), max_tokens=300)
j = get_json(r)
results["test1_alertness"] = j is not None
print(f"  JSON: {j}")
print(f"  {'PASS' if j else 'FAIL'} — {'Valid JSON returned' if j else 'No JSON — STILL BROKEN'}")

# %%
print("\nTEST 2: BREATHING — Chest Indrawing")
p = PromptRegistry.get("breathing.detect_chest_indrawing")
r = ask(p.render_multimodal(media={"image": "/tmp/test.jpg"}), max_tokens=300)
j = get_json(r)
results["test2_indrawing"] = j is not None
print(f"  JSON: {j}")
print(f"  {'PASS' if j else 'FAIL'}")

# %%
print("\nTEST 3: PROTOCOL — Breathing Classification (deterministic)")
proto_pass = 0
proto_total = 5
for age, rate, exp in [
    (6, 55, "pneumonia"), (6, 42, "no_pneumonia"),
    (24, 45, "pneumonia"), (24, 35, "no_pneumonia"), (10, 50, "pneumonia"),
]:
    c = classify_breathing(age_months=age, breathing_rate=rate, has_cough=True)
    ok = exp in c.classification.value
    if ok:
        proto_pass += 1
    print(f"  {'PASS' if ok else 'FAIL'} | Age {age}mo, Rate {rate} -> {c.classification.value}")
results["test3_protocol"] = proto_pass == proto_total

# %%
print("\nTEST 4: DIARRHEA — Dehydration Signs")
p = PromptRegistry.get("diarrhea.assess_dehydration_signs")
r = ask(p.render_multimodal(media={"image": "/tmp/test.jpg"}), max_tokens=300)
j = get_json(r)
results["test4_dehydration"] = j is not None
print(f"  JSON: {j}")
print(f"  {'PASS' if j else 'FAIL'}")

# %%
print("\nTEST 5 [RE-RUN]: NUTRITION — Wasting Assessment")
p = PromptRegistry.get("nutrition.assess_wasting")
r = ask(p.render_multimodal(media={"image": "/tmp/test.jpg"}), max_tokens=300)
j = get_json(r)
results["test5_wasting"] = j is not None
print(f"  JSON: {j}")
print(f"  {'PASS' if j else 'FAIL'} — {'Valid JSON returned' if j else 'No JSON — STILL BROKEN'}")

# %%
print("\nTEST 6 [IMPROVED]: TREATMENT — Swahili (should be PLAIN TEXT, not JSON)")
p = PromptRegistry.get("treatment.generate_plan")
r = ask(p.render(
    classifications="Pneumonia",
    urgency="YELLOW",
    language="Swahili",
    child_age_months=6,
), max_tokens=500)
# Success = plain text (no JSON wrapping)
is_json = get_json(r) is not None
is_plain_text = not is_json and len(r.strip()) > 50
results["test6_treatment_swahili"] = is_plain_text
print(f"\n{r}")
print(f"\n  {'PASS' if is_plain_text else 'FAIL'} — {'Plain text output' if is_plain_text else 'Still returning JSON!'}")

# %%
print("\nTEST 7: GOLDEN SCENARIOS")
from malaika.evaluation.golden_scenarios import GOLDEN_SCENARIOS
passed = 0
for s in GOLDEN_SCENARIOS:
    result = classify_assessment(age_months=s.age_months, **s.findings)
    actual = set(c.value for c in result.all_classification_types)
    expected = set(c.value for c in s.expected_classifications)
    if expected.issubset(actual) and result.severity == s.expected_severity:
        passed += 1
        print(f"  PASS | {s.name}")
    else:
        print(f"  FAIL | {s.name} — expected {expected}, got {actual}")
results["test7_golden"] = passed == len(GOLDEN_SCENARIOS)
print(f"\n  Result: {passed}/{len(GOLDEN_SCENARIOS)}")

# %%
print("\nTEST 8: JSON RELIABILITY (5 prompts)")
prompts_to_test = [
    "danger.assess_alertness",
    "breathing.detect_chest_indrawing",
    "diarrhea.assess_dehydration_signs",
    "nutrition.assess_wasting",
    "nutrition.detect_edema",
]
json_pass = 0
for name in prompts_to_test:
    p = PromptRegistry.get(name)
    r = ask(p.render_multimodal(media={"image": "/tmp/test.jpg"}), max_tokens=300)
    j = get_json(r)
    if j:
        json_pass += 1
        print(f"  PASS | {name}")
    else:
        print(f"  FAIL | {name}: {r[:80]}")
results["test8_json"] = json_pass == len(prompts_to_test)
print(f"\n  JSON: {json_pass}/{len(prompts_to_test)}")

# %% [markdown]
# ## 4. ICBHI Real Data — Spectrogram Pipeline Test
#
# This is the NEW test for Day 4. Convert real ICBHI breath sounds to
# spectrograms and test Gemma 4 vision classification.

# %%
print("=" * 60)
print("SECTION B: REAL ICBHI DATA — SPECTROGRAM CLASSIFICATION")
print("=" * 60)

import librosa

# Download ICBHI dataset via Kaggle API (works on both Colab and Kaggle)
ICBHI_DIR = Path("/tmp/icbhi_data")
ICBHI_INNER = ICBHI_DIR / "Respiratory_Sound_Database" / "Respiratory_Sound_Database"

# Check Kaggle-native path first (if running on Kaggle with dataset attached)
KAGGLE_NATIVE = Path("/kaggle/input/respiratory-sound-database/Respiratory_Sound_Database/Respiratory_Sound_Database")

if KAGGLE_NATIVE.exists():
    audio_dir = KAGGLE_NATIVE / "audio_and_txt_files"
    print(f"ICBHI dataset found at Kaggle native path")
elif ICBHI_INNER.exists():
    audio_dir = ICBHI_INNER / "audio_and_txt_files"
    print(f"ICBHI dataset found at {ICBHI_INNER}")
else:
    print("Downloading ICBHI dataset via Kaggle API...")
    ICBHI_DIR.mkdir(parents=True, exist_ok=True)
    dl_result = subprocess.run(
        ["kaggle", "datasets", "download", "-d", "vbookshelf/respiratory-sound-database",
         "-p", str(ICBHI_DIR), "--unzip"],
        capture_output=True, text=True,
    )
    if dl_result.returncode == 0:
        print(f"  Download complete")
        audio_dir = ICBHI_INNER / "audio_and_txt_files"
    else:
        print(f"  Download failed: {dl_result.stderr}")
        print("  Set KAGGLE_USERNAME and KAGGLE_KEY secrets to enable download")
        audio_dir = None

if audio_dir and audio_dir.exists():
    all_wavs = sorted(audio_dir.glob("*.wav"))
    print(f"ICBHI dataset: {len(all_wavs)} audio files")
else:
    print("ICBHI dataset NOT available — skipping real data tests")
    all_wavs = []

SPEC_DIR = Path("/tmp/test_spectrograms")
SPEC_DIR.mkdir(exist_ok=True)

# %%
# Parse annotations to get labels
def parse_icbhi_label(txt_path: Path) -> str:
    """Parse ICBHI annotation file to get overall label."""
    has_crackle = False
    has_wheeze = False
    with open(txt_path) as f:
        for line in f:
            fields = line.strip().split()
            if len(fields) >= 4:
                if int(fields[2]) == 1:
                    has_crackle = True
                if int(fields[3]) == 1:
                    has_wheeze = True
    if has_crackle and has_wheeze:
        return "both"
    if has_crackle:
        return "crackle"
    if has_wheeze:
        return "wheeze"
    return "normal"


# Select a stratified sample of 20 recordings for testing
if all_wavs:
    # Get labels for all files
    labeled_files = []
    for wav in all_wavs:
        txt = wav.with_suffix(".txt")
        if txt.exists():
            label = parse_icbhi_label(txt)
            labeled_files.append((wav, label))

    # Stratified sample: 5 per category
    from collections import defaultdict
    import random
    random.seed(42)

    by_label = defaultdict(list)
    for wav, label in labeled_files:
        by_label[label].append(wav)

    test_files = []
    for label in ["normal", "wheeze", "crackle", "both"]:
        available = by_label.get(label, [])
        sample = random.sample(available, min(5, len(available)))
        test_files.extend([(f, label) for f in sample])

    print(f"\nSelected {len(test_files)} test files:")
    from collections import Counter
    counts = Counter(label for _, label in test_files)
    for label, count in sorted(counts.items()):
        print(f"  {label}: {count}")

# %% [markdown]
# ### 4a. Generate Spectrograms from Real Audio

# %%
if all_wavs:
    print("\nGenerating spectrograms from real ICBHI audio...")
    SPEC_PARAMS = dict(
        sr=22050, n_fft=2048, hop_length=512, n_mels=128,
        fmin=50, fmax=4000,
    )

    spec_test_data = []
    for wav_path, label in test_files:
        spec_path = SPEC_DIR / f"{wav_path.stem}_spec.png"
        try:
            y, sr = librosa.load(str(wav_path), sr=SPEC_PARAMS["sr"], mono=True)
            if len(y) == 0:
                continue

            mel_spec = librosa.feature.melspectrogram(y=y, sr=sr, **{k: v for k, v in SPEC_PARAMS.items() if k != "sr"})
            mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)

            spec_min, spec_max = mel_spec_db.min(), mel_spec_db.max()
            if spec_max - spec_min > 0:
                normalized = ((mel_spec_db - spec_min) / (spec_max - spec_min) * 255).astype(np.uint8)
            else:
                normalized = np.zeros_like(mel_spec_db, dtype=np.uint8)

            normalized = np.flip(normalized, axis=0)
            img = Image.fromarray(normalized, mode="L").resize((512, 256), Image.Resampling.LANCZOS).convert("RGB")
            img.save(str(spec_path))

            duration = len(y) / sr
            spec_test_data.append({
                "wav": wav_path, "spec": spec_path, "label": label, "duration": duration,
            })
            print(f"  {wav_path.name} ({duration:.1f}s) -> {spec_path.name} [{label}]")
        except Exception as e:
            print(f"  SKIP {wav_path.name}: {e}")

    print(f"\nGenerated {len(spec_test_data)} spectrograms")

# %% [markdown]
# ### 4b. Test Gemma 4 Vision on Real Spectrograms (Base Model — No Fine-Tuning)

# %%
if all_wavs and spec_test_data:
    print("\nTesting Gemma 4 vision on REAL breath sound spectrograms...")
    print("(Base model — no fine-tuning yet — establishing baseline)\n")

    spec_prompt = PromptRegistry.get("breathing.classify_breath_sounds_from_spectrogram")
    spec_results = []

    for item in spec_test_data:
        spec_img = Image.open(item["spec"]).convert("RGB")

        messages = [
            {"role": "user", "content": [
                {"type": "image"},
                {"type": "text", "text": spec_prompt.user_template},
            ]},
        ]

        print(f"  [{item['label']:>7s}] {item['wav'].name}:")
        r = ask_with_image(messages, images=[spec_img], max_tokens=200)
        j = get_json(r)

        if j:
            predicted_normal = j.get("normal", True)
            predicted_wheeze = j.get("wheeze", False)
            predicted_crackle = j.get("crackles", False)
            confidence = j.get("confidence", 0)

            # Simple accuracy check
            actual_normal = item["label"] == "normal"
            actual_wheeze = item["label"] in ("wheeze", "both")
            actual_crackle = item["label"] in ("crackle", "both")

            wheeze_correct = predicted_wheeze == actual_wheeze
            crackle_correct = predicted_crackle == actual_crackle

            status = "CORRECT" if wheeze_correct and crackle_correct else "WRONG"
            print(f"    {status} | pred: wheeze={predicted_wheeze} crackle={predicted_crackle} "
                  f"normal={predicted_normal} conf={confidence}")
            print(f"    desc: {j.get('description', '')[:80]}")

            spec_results.append({
                "label": item["label"],
                "json_ok": True,
                "wheeze_correct": wheeze_correct,
                "crackle_correct": crackle_correct,
                "confidence": confidence,
            })
        else:
            print(f"    FAIL (no JSON): {r[:80]}")
            spec_results.append({"label": item["label"], "json_ok": False})

    # Summary
    json_ok = sum(1 for r in spec_results if r["json_ok"])
    wheeze_ok = sum(1 for r in spec_results if r.get("wheeze_correct"))
    crackle_ok = sum(1 for r in spec_results if r.get("crackle_correct"))
    both_ok = sum(1 for r in spec_results if r.get("wheeze_correct") and r.get("crackle_correct"))
    total = len(spec_results)

    print(f"\n  SPECTROGRAM BASELINE RESULTS (no fine-tuning):")
    print(f"    JSON parse:     {json_ok}/{total}")
    print(f"    Wheeze correct: {wheeze_ok}/{total}")
    print(f"    Crackle correct:{crackle_ok}/{total}")
    print(f"    Both correct:   {both_ok}/{total} ({100*both_ok/total:.0f}%)")
    print(f"\n  This is the BASELINE — fine-tuning should improve significantly.")

    results["test9_spectrogram_json"] = json_ok == total
    results["test9_spectrogram_accuracy"] = both_ok / total if total > 0 else 0

# %% [markdown]
# ## 5. Latency Benchmarks

# %%
print("=" * 60)
print("SECTION C: LATENCY BENCHMARKS")
print("=" * 60)

benchmarks = {}

# Text-only latency
print("\nText-only (treatment prompt):")
p = PromptRegistry.get("treatment.generate_plan")
t0 = time.monotonic()
r = ask(p.render(
    classifications="Pneumonia", urgency="YELLOW",
    language="English", child_age_months=12,
), max_tokens=300)
benchmarks["text_only_ms"] = (time.monotonic() - t0) * 1000

# Vision latency
print("\nVision (chest indrawing):")
p = PromptRegistry.get("breathing.detect_chest_indrawing")
t0 = time.monotonic()
r = ask(p.render_multimodal(media={"image": "/tmp/test.jpg"}), max_tokens=200)
benchmarks["vision_ms"] = (time.monotonic() - t0) * 1000

# Spectrogram generation latency (if ICBHI available)
if all_wavs and spec_test_data:
    print("\nSpectrogram generation (audio -> PNG):")
    t0 = time.monotonic()
    y, sr = librosa.load(str(spec_test_data[0]["wav"]), sr=22050, mono=True)
    mel_spec = librosa.feature.melspectrogram(y=y, sr=sr, n_fft=2048, hop_length=512, n_mels=128, fmin=50, fmax=4000)
    mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
    benchmarks["spectrogram_gen_ms"] = (time.monotonic() - t0) * 1000
    print(f"  {benchmarks['spectrogram_gen_ms']:.0f}ms")

    print("\nSpectrogram vision (spec image -> classification):")
    spec_img = Image.open(spec_test_data[0]["spec"]).convert("RGB")
    messages = [{"role": "user", "content": [
        {"type": "image"},
        {"type": "text", "text": "Classify the breath sounds in this mel-spectrogram. Report JSON."},
    ]}]
    t0 = time.monotonic()
    r = ask_with_image(messages, images=[spec_img], max_tokens=200)
    benchmarks["spectrogram_vision_ms"] = (time.monotonic() - t0) * 1000

print(f"\nBenchmarks:")
for k, v in benchmarks.items():
    print(f"  {k}: {v:.0f}ms")

# %% [markdown]
# ## 6. Final Summary

# %%
print("=" * 60)
print("DAY 4 TEST SUMMARY")
print("=" * 60)
print(f"Model:           {MODEL_NAME}")
print(f"GPU:             {torch.cuda.get_device_name(0)}")
print(f"Load time:       {load_time:.0f}s")
print(f"Environment:     {ENV}")
print()

print("Session 1 Re-verification:")
for key in ["test1_alertness", "test2_indrawing", "test3_protocol",
            "test4_dehydration", "test5_wasting", "test6_treatment_swahili",
            "test7_golden", "test8_json"]:
    status = "PASS" if results.get(key) else "FAIL"
    print(f"  {status} | {key}")

if "test9_spectrogram_json" in results:
    print(f"\nSpectrogram Pipeline (ICBHI real data):")
    print(f"  JSON parse:  {'PASS' if results['test9_spectrogram_json'] else 'FAIL'}")
    print(f"  Baseline acc: {results['test9_spectrogram_accuracy']*100:.0f}%")

print(f"\nLatency:")
for k, v in benchmarks.items():
    print(f"  {k}: {v:.0f}ms")

all_pass = all(v for k, v in results.items() if isinstance(v, bool))
print(f"\nOverall: {'ALL PASS' if all_pass else 'SOME FAILURES — check above'}")
print("=" * 60)
