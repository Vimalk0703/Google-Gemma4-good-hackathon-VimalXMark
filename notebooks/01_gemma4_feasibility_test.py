# %% [markdown]
# # Malaika — Gemma 4 Feasibility Test
#
# **Goal**: Verify Gemma 4 E4B loads in 4-bit, test all modalities (text, image, audio, video),
# measure VRAM usage and latency.
#
# **Run on**: Kaggle with T4 GPU enabled
#
# **Prerequisites**:
# - Accept Gemma 4 license at https://huggingface.co/google/gemma-4-E4B-it
# - Add HF_TOKEN to Kaggle Secrets (Settings → Add-ons → Secrets)

# %% [markdown]
# ## 1. Setup

# %%
# Install dependencies — MUST install transformers from source for Gemma 4 support
# The PyPI release does not yet include the "gemma4" model type
!pip install -q git+https://github.com/huggingface/transformers.git bitsandbytes accelerate torch

# %%
# Authenticate with HuggingFace
from huggingface_hub import login
from kaggle_secrets import UserSecretsClient

secrets = UserSecretsClient()
login(token=secrets.get_secret("HF_TOKEN"))

# %%
import time
import torch
import json

print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM total: {torch.cuda.get_device_properties(0).total_mem / 1024**3:.1f} GB")

# %% [markdown]
# ## 2. Load Gemma 4 E4B in 4-bit

# %%
from transformers import AutoProcessor, AutoModelForImageTextToText, BitsAndBytesConfig

MODEL_NAME = "google/gemma-4-E4B-it"

print(f"Loading {MODEL_NAME} in 4-bit quantization...")
start = time.monotonic()

quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
)

processor = AutoProcessor.from_pretrained(MODEL_NAME)
model = AutoModelForImageTextToText.from_pretrained(
    MODEL_NAME,
    device_map="auto",
    quantization_config=quantization_config,
)

load_time = time.monotonic() - start
vram_after_load = torch.cuda.memory_allocated() / 1024**3

print(f"✓ Model loaded in {load_time:.1f}s")
print(f"✓ VRAM usage: {vram_after_load:.1f} GB")

# %% [markdown]
# ## 3. Helper function

# %%
def generate(messages, max_tokens=256):
    """Generate a response from Gemma 4."""
    start = time.monotonic()
    inputs = processor.apply_chat_template(
        messages,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
        add_generation_prompt=True,
    ).to(model.device)

    with torch.inference_mode():
        outputs = model.generate(**inputs, max_new_tokens=max_tokens)

    # Decode only the NEW tokens (skip the input tokens)
    new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
    result = processor.decode(new_tokens, skip_special_tokens=True)
    latency = (time.monotonic() - start) * 1000

    print(f"  Latency: {latency:.0f}ms | Output tokens: {len(new_tokens)}")
    return result

# %% [markdown]
# ## 4. Test: Text Reasoning (IMCI Knowledge)

# %%
print("=" * 60)
print("TEST 1: IMCI Text Reasoning")
print("=" * 60)

messages = [
    {"role": "system", "content": "You are a medical assistant following WHO IMCI protocol. Be precise."},
    {"role": "user", "content": (
        "A 6-month-old child has a breathing rate of 55 breaths per minute and a cough. "
        "According to WHO IMCI guidelines, is this fast breathing? What is the threshold "
        "for this age group? Respond with a JSON object: "
        '{"is_fast_breathing": true/false, "threshold": <number>, "classification": "<text>"}'
    )},
]
result = generate(messages, max_tokens=200)
print(f"\nResponse:\n{result}")

# %% [markdown]
# ## 5. Test: Image Analysis (Chest/Skin)

# %%
# NOTE: For this test, upload a sample medical image to Kaggle
# or use a placeholder test with a generated image.
# In production, this will analyze real clinical images.

from PIL import Image
import numpy as np

# Create a simple test image (placeholder — replace with real clinical image)
test_image = Image.fromarray(np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8))
test_image.save("/tmp/test_image.jpg")

print("=" * 60)
print("TEST 2: Image Analysis")
print("=" * 60)

messages = [
    {"role": "system", "content": (
        "You are analyzing a medical image for the WHO IMCI protocol. "
        "Respond ONLY with a JSON object."
    )},
    {"role": "user", "content": [
        {"type": "image", "image": "/tmp/test_image.jpg"},
        {"type": "text", "text": (
            "Examine this image. Report what you observe about the subject's appearance. "
            'Respond with JSON: {"description": "<what you see>", "confidence": <0.0-1.0>}'
        )},
    ]},
]
result = generate(messages, max_tokens=200)
print(f"\nResponse:\n{result}")

# %% [markdown]
# ## 6. Test: Audio Analysis (if supported)

# %%
# NOTE: Gemma 4 E4B supports audio input natively.
# Create a test audio file to verify the pipeline works.

import wave
import struct

# Generate a simple 1-second sine wave test audio
def create_test_wav(filepath, duration=1.0, freq=440, sample_rate=16000):
    """Create a simple WAV file for testing."""
    n_samples = int(duration * sample_rate)
    samples = []
    for i in range(n_samples):
        sample = int(32767 * 0.5 * np.sin(2 * np.pi * freq * i / sample_rate))
        samples.append(struct.pack('<h', sample))

    with wave.open(filepath, 'w') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b''.join(samples))

create_test_wav("/tmp/test_audio.wav")

print("=" * 60)
print("TEST 3: Audio Analysis")
print("=" * 60)

try:
    messages = [
        {"role": "system", "content": (
            "You are analyzing an audio recording. "
            "Respond ONLY with a JSON object."
        )},
        {"role": "user", "content": [
            {"type": "audio", "audio": "/tmp/test_audio.wav"},
            {"type": "text", "text": (
                "Describe what you hear in this audio. "
                'Respond with JSON: {"description": "<what you hear>", "confidence": <0.0-1.0>}'
            )},
        ]},
    ]
    result = generate(messages, max_tokens=200)
    print(f"\nResponse:\n{result}")
    print("\n✓ Audio modality WORKS")
except Exception as e:
    print(f"\n✗ Audio modality FAILED: {e}")

# %% [markdown]
# ## 7. Test: JSON Output Reliability

# %%
print("=" * 60)
print("TEST 4: JSON Output Reliability (5 attempts)")
print("=" * 60)

json_success = 0
for i in range(5):
    messages = [
        {"role": "user", "content": (
            "A child shows sunken eyes and slow skin pinch. "
            "Report ONLY a JSON object, nothing else: "
            '{"sunken_eyes": true/false, "skin_pinch_slow": true/false, '
            '"dehydration_level": "none|some|severe", "confidence": <0.0-1.0>}'
        )},
    ]
    result = generate(messages, max_tokens=150)
    try:
        # Try to extract JSON
        import re
        json_match = re.search(r'\{[^{}]*\}', result)
        if json_match:
            parsed = json.loads(json_match.group(0))
            json_success += 1
            print(f"  Attempt {i+1}: ✓ Valid JSON — {parsed}")
        else:
            print(f"  Attempt {i+1}: ✗ No JSON found in: {result[:100]}")
    except json.JSONDecodeError:
        print(f"  Attempt {i+1}: ✗ Invalid JSON: {result[:100]}")

print(f"\nJSON reliability: {json_success}/5 ({json_success*20}%)")

# %% [markdown]
# ## 8. Test: Multilingual (Swahili)

# %%
print("=" * 60)
print("TEST 5: Multilingual — Swahili")
print("=" * 60)

messages = [
    {"role": "system", "content": (
        "You are Malaika, a child health assistant. "
        "Respond in Swahili. Be clear and simple."
    )},
    {"role": "user", "content": (
        "Mtoto wangu ana homa na kikohozi. Nifanye nini? "
        "(My child has fever and cough. What should I do?)"
    )},
]
result = generate(messages, max_tokens=300)
print(f"\nSwahili response:\n{result}")

# %% [markdown]
# ## 9. Summary

# %%
print("\n" + "=" * 60)
print("FEASIBILITY TEST SUMMARY")
print("=" * 60)
print(f"Model: {MODEL_NAME}")
print(f"Quantization: 4-bit (BitsAndBytes)")
print(f"Load time: {load_time:.1f}s")
print(f"VRAM usage: {vram_after_load:.1f} GB")
print(f"JSON reliability: {json_success}/5")
print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"Total VRAM: {torch.cuda.get_device_properties(0).total_mem / 1024**3:.1f} GB")
print("=" * 60)
print()
print("NEXT STEPS:")
print("  1. If VRAM > 8GB: try E2B model instead")
print("  2. If JSON reliability < 80%: strengthen prompt engineering")
print("  3. If audio fails: test different audio formats/durations")
print("  4. Run breath sound classification test with ICBHI samples")
