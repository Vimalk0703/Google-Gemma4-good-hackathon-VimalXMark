# %% [markdown]
# # Malaika — Fine-Tune Gemma 4 E4B for Breath Sound Classification (Spectrogram Vision)
#
# **Goal**: Train a QLoRA adapter to classify pediatric breath sounds from
# mel-spectrogram images using Gemma 4's vision capability.
#
# **Key Insight**: Gemma 4 cannot process audio natively, but its vision works
# excellently. By converting audio to spectrogram images, we leverage the working
# modality to solve the audio classification problem.
#
# **Pipeline**: Audio WAV → librosa mel-spectrogram → PNG image → Gemma 4 vision
#
# **Dataset**: ICBHI 2017 Respiratory Sound Database (920 recordings)
# **Method**: Unsloth QLoRA 4-bit on Gemma 4 E4B vision
# **Hardware**: Colab/Kaggle T4 16GB GPU
# **Time**: ~2-3 hours
#
# **This notebook targets the Unsloth $10K prize.**

# %% [markdown]
# ## 1. Setup

# %%
# MUST install transformers from source for Gemma 4 support
# librosa for spectrogram generation
!pip install -q git+https://github.com/huggingface/transformers.git peft trl datasets bitsandbytes accelerate librosa Pillow soundfile kaggle

# %%
# Authenticate — works on both Colab and Kaggle
from huggingface_hub import login
import os, subprocess

try:
    from kaggle_secrets import UserSecretsClient
    secrets = UserSecretsClient()
    login(token=secrets.get_secret("HF_TOKEN"))
    KAGGLE_USERNAME = secrets.get_secret("KAGGLE_USERNAME")
    KAGGLE_KEY = secrets.get_secret("KAGGLE_KEY")
    print("Authenticated via Kaggle secrets")
except ModuleNotFoundError:
    try:
        from google.colab import userdata
        login(token=userdata.get("HF_TOKEN"))
        KAGGLE_USERNAME = userdata.get("KAGGLE_USERNAME")
        KAGGLE_KEY = userdata.get("KAGGLE_KEY")
        print("Authenticated via Colab secrets")
    except Exception:
        login()
        KAGGLE_USERNAME = os.environ.get("KAGGLE_USERNAME", "")
        KAGGLE_KEY = os.environ.get("KAGGLE_KEY", "")
        print("Authenticated via manual login")

# Set up Kaggle API credentials for dataset download
os.makedirs(os.path.expanduser("~/.kaggle"), exist_ok=True)
import json as _json
with open(os.path.expanduser("~/.kaggle/kaggle.json"), "w") as f:
    _json.dump({"username": KAGGLE_USERNAME, "key": KAGGLE_KEY}, f)
os.chmod(os.path.expanduser("~/.kaggle/kaggle.json"), 0o600)

# %%
import json
import os
import random
import tempfile
from collections import Counter
from pathlib import Path

import numpy as np
import torch

print(f"CUDA: {torch.cuda.is_available()}")
print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"VRAM: {torch.cuda.get_device_properties(0).total_mem / 1024**3:.1f} GB")

# %% [markdown]
# ## 2. Download and Prepare ICBHI Dataset
#
# The ICBHI 2017 dataset contains 920 respiratory sound recordings with
# annotations for: normal, wheeze, crackle, both (wheeze + crackle).
#
# **Add the dataset via Kaggle sidebar**: Search "respiratory-sound-database" by vbookshelf

# %%
# Auto-detect dataset location (Kaggle native) or download via API (Colab)
KAGGLE_NATIVE = Path("/kaggle/input/respiratory-sound-database/Respiratory_Sound_Database/Respiratory_Sound_Database")
ICBHI_DIR = Path("/tmp/icbhi_data")
ICBHI_INNER = ICBHI_DIR / "Respiratory_Sound_Database" / "Respiratory_Sound_Database"

if KAGGLE_NATIVE.exists():
    audio_dir = KAGGLE_NATIVE / "audio_and_txt_files"
    print("ICBHI dataset found at Kaggle native path")
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
        print("  Download complete")
        audio_dir = ICBHI_INNER / "audio_and_txt_files"
    else:
        print(f"  Download failed: {dl_result.stderr}")
        audio_dir = None

if audio_dir and audio_dir.exists():
    audio_files = list(audio_dir.glob("*.wav"))
    print(f"ICBHI dataset: {len(audio_files)} audio files")
else:
    print("ICBHI dataset NOT available — will use dummy data")
    audio_files = []

# %% [markdown]
# ## 3. Parse ICBHI Annotations

# %%
def parse_icbhi_annotations(audio_dir: Path) -> list[dict]:
    """Parse ICBHI annotation files into structured records."""
    records = []

    for txt_file in sorted(audio_dir.glob("*.txt")):
        wav_file = txt_file.with_suffix(".wav")
        if not wav_file.exists():
            continue

        parts = txt_file.stem.split("_")
        patient_id = parts[0] if parts else "unknown"

        has_crackle = False
        has_wheeze = False
        cycle_count = 0

        with open(txt_file) as f:
            for line in f:
                fields = line.strip().split()
                if len(fields) >= 4:
                    cycle_count += 1
                    if int(fields[2]) == 1:
                        has_crackle = True
                    if int(fields[3]) == 1:
                        has_wheeze = True

        if has_crackle and has_wheeze:
            label = "both"
        elif has_crackle:
            label = "crackle"
        elif has_wheeze:
            label = "wheeze"
        else:
            label = "normal"

        records.append({
            "audio_path": str(wav_file),
            "patient_id": patient_id,
            "label": label,
            "has_crackle": has_crackle,
            "has_wheeze": has_wheeze,
            "cycle_count": cycle_count,
        })

    return records


if audio_files:
    records = parse_icbhi_annotations(audio_dir)
    label_counts = Counter(r["label"] for r in records)
    print(f"Parsed {len(records)} recordings:")
    for label, count in sorted(label_counts.items()):
        print(f"  {label}: {count}")

# %% [markdown]
# ## 4. Generate Mel-Spectrogram Images
#
# Convert all ICBHI audio files to mel-spectrogram PNGs.
# Parameters tuned for pediatric breath sounds (50-4000 Hz range).

# %%
import librosa
from PIL import Image

SPEC_DIR = Path("/tmp/spectrograms")
SPEC_DIR.mkdir(exist_ok=True)

# Parameters tuned for breath sounds
SPEC_SR = 22050
SPEC_N_FFT = 2048
SPEC_HOP_LENGTH = 512
SPEC_N_MELS = 128
SPEC_FMIN = 50      # Captures low grunting
SPEC_FMAX = 4000    # Captures high wheeze/stridor
SPEC_WIDTH = 512
SPEC_HEIGHT = 256


def audio_to_spectrogram_image(audio_path: Path, output_path: Path) -> bool:
    """Convert audio file to mel-spectrogram PNG image."""
    try:
        y, sr = librosa.load(str(audio_path), sr=SPEC_SR, mono=True)
        if len(y) == 0:
            return False

        mel_spec = librosa.feature.melspectrogram(
            y=y, sr=sr,
            n_fft=SPEC_N_FFT, hop_length=SPEC_HOP_LENGTH, n_mels=SPEC_N_MELS,
            fmin=SPEC_FMIN, fmax=SPEC_FMAX,
        )
        mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)

        # Normalize to 0-255
        spec_min, spec_max = mel_spec_db.min(), mel_spec_db.max()
        if spec_max - spec_min > 0:
            normalized = ((mel_spec_db - spec_min) / (spec_max - spec_min) * 255).astype(np.uint8)
        else:
            normalized = np.zeros_like(mel_spec_db, dtype=np.uint8)

        # Flip vertically (low freq at bottom)
        normalized = np.flip(normalized, axis=0)

        img = Image.fromarray(normalized, mode="L").resize(
            (SPEC_WIDTH, SPEC_HEIGHT), Image.Resampling.LANCZOS
        ).convert("RGB")
        img.save(str(output_path))
        return True
    except Exception as e:
        print(f"  Failed: {audio_path.name}: {e}")
        return False


if audio_files:
    print("Generating spectrograms...")
    spec_records = []
    for i, record in enumerate(records):
        audio_path = Path(record["audio_path"])
        spec_path = SPEC_DIR / f"{audio_path.stem}_spec.png"

        if audio_to_spectrogram_image(audio_path, spec_path):
            record["spectrogram_path"] = str(spec_path)
            spec_records.append(record)

        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{len(records)} done")

    print(f"\nGenerated {len(spec_records)}/{len(records)} spectrograms")
    records = spec_records  # Use only records with successful spectrograms

# %% [markdown]
# ## 5. Create Vision Instruction Pairs
#
# Format ICBHI records as Gemma 4 vision instruction/response pairs.
# The instruction references the spectrogram image, and the response
# is the expected JSON classification.

# %%
def create_vision_instruction_pairs(records: list[dict]) -> list[dict]:
    """Convert ICBHI records to Gemma 4 vision instruction pairs with spectrogram images."""
    pairs = []

    for record in records:
        response = json.dumps({
            "wheeze": record["has_wheeze"],
            "stridor": False,    # ICBHI doesn't annotate stridor
            "grunting": False,   # ICBHI doesn't annotate grunting
            "crackles": record["has_crackle"],
            "normal": record["label"] == "normal",
            "confidence": 0.9,
            "description": _describe_breath_sounds(record),
        })

        pair = {
            "spectrogram_path": record["spectrogram_path"],
            "instruction": (
                "This is a mel-spectrogram image of a child's breathing audio recorded by a phone "
                "microphone placed near the child's chest/mouth.\n\n"
                "The image shows:\n"
                "- Vertical axis: frequency (50 Hz at bottom to 4000 Hz at top)\n"
                "- Horizontal axis: time (left to right)\n"
                "- Brightness: intensity (brighter = louder)\n\n"
                "Interpret the spectrogram to classify the breath sounds.\n\n"
                "Report ONLY a JSON object: "
                '{"wheeze": true/false, "stridor": true/false, "grunting": true/false, '
                '"crackles": true/false, "normal": true/false, '
                '"confidence": <0.0-1.0>, '
                '"description": "<what patterns you see>"}'
            ),
            "response": response,
            "label": record["label"],
        }
        pairs.append(pair)

    return pairs


def _describe_breath_sounds(record: dict) -> str:
    """Generate a natural description of the breath sounds."""
    if record["label"] == "normal":
        return "Normal vesicular breath sounds. No adventitious sounds detected."
    parts = []
    if record["has_wheeze"]:
        parts.append("Wheezing detected — continuous horizontal bright bands in the 200-1000 Hz range")
    if record["has_crackle"]:
        parts.append("Crackles detected — discontinuous vertical bright spots scattered across the spectrogram")
    return ". ".join(parts) + "."


if audio_files:
    pairs = create_vision_instruction_pairs(records)
    print(f"Created {len(pairs)} vision instruction pairs")
    print(f"\nExample pair:")
    print(f"  Spectrogram: {pairs[0]['spectrogram_path']}")
    print(f"  Label: {pairs[0]['label']}")
    print(f"  Response: {pairs[0]['response']}")

# %% [markdown]
# ## 6. Train/Test Split (Patient-Level)
#
# Split by patient ID to avoid data leakage.

# %%
def patient_split(pairs: list[dict], records: list[dict], test_ratio: float = 0.2) -> tuple[list, list]:
    """Split by patient ID to avoid data leakage."""
    patient_ids = list(set(r["patient_id"] for r in records))
    random.seed(42)
    random.shuffle(patient_ids)

    split_idx = int(len(patient_ids) * (1 - test_ratio))
    train_patients = set(patient_ids[:split_idx])

    train_pairs = []
    test_pairs = []
    for pair, record in zip(pairs, records):
        if record["patient_id"] in train_patients:
            train_pairs.append(pair)
        else:
            test_pairs.append(pair)

    return train_pairs, test_pairs


if audio_files:
    train_pairs, test_pairs = patient_split(pairs, records)
    print(f"Train: {len(train_pairs)} | Test: {len(test_pairs)}")
    for split_name, split_pairs in [("Train", train_pairs), ("Test", test_pairs)]:
        counts = Counter(p["label"] for p in split_pairs)
        print(f"  {split_name}: {dict(counts)}")

# %% [markdown]
# ## 7. Prepare Training Data
#
# Convert pairs into tokenized training examples with spectrogram images.
# We use the processor to create input_ids + pixel_values for each example.

# %%
from transformers import AutoProcessor, AutoModelForImageTextToText, BitsAndBytesConfig
import re

MODEL_NAME = "google/gemma-4-E4B-it"

print(f"Loading processor for {MODEL_NAME}...")
processor = AutoProcessor.from_pretrained(MODEL_NAME)
tokenizer = processor.tokenizer

SYSTEM_MSG = (
    "You are Malaika, a medical audio analysis assistant "
    "following the WHO IMCI protocol. You analyze mel-spectrogram "
    "images of breath sounds to detect abnormalities. "
    "Respond ONLY in the format specified. Do NOT use thinking mode."
)


def tokenize_example(pair: dict) -> dict:
    """Tokenize a single training example with spectrogram image."""
    spec_img = Image.open(pair["spectrogram_path"]).convert("RGB")

    messages = [
        {"role": "user", "content": [
            {"type": "image"},
            {"type": "text", "text": f"{SYSTEM_MSG}\n\n{pair['instruction']}"},
        ]},
        {"role": "assistant", "content": [
            {"type": "text", "text": pair["response"]},
        ]},
    ]

    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    inputs = processor(text=text, images=[spec_img], return_tensors="pt", padding=False, truncation=True, max_length=2048)

    input_ids = inputs["input_ids"].squeeze(0)
    labels = input_ids.clone()

    # Mask everything before the assistant response (only train on output)
    response_text = pair["response"]
    response_tokens = tokenizer.encode(response_text, add_special_tokens=False)
    response_len = len(response_tokens)
    if response_len > 0 and len(labels) > response_len:
        labels[:-response_len] = -100

    return {
        "input_ids": input_ids,
        "attention_mask": inputs["attention_mask"].squeeze(0),
        "pixel_values": inputs.get("pixel_values", inputs.get("pixel_values_videos")),
        "labels": labels,
    }


# Test tokenization with one example
if audio_files:
    test_tok = tokenize_example(pairs[0])
    print(f"Tokenized example: input_ids={test_tok['input_ids'].shape}, labels masked except last {(test_tok['labels'] != -100).sum()} tokens")

# %% [markdown]
# ## 8. Load Model in 4-bit

# %%
print(f"Loading {MODEL_NAME} in 4-bit...")
t0 = time.monotonic()

model = AutoModelForImageTextToText.from_pretrained(
    MODEL_NAME,
    device_map="auto",
    quantization_config=BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_quant_type="nf4",
    ),
    torch_dtype=torch.float16,
)

load_time = time.monotonic() - t0
print(f"Model loaded in {load_time:.0f}s")
print(f"  VRAM: {torch.cuda.memory_allocated() / 1024**3:.1f} GB")

# %% [markdown]
# ## 9. Add LoRA Adapter (PEFT)
#
# We target attention and MLP modules in both vision encoder and language model.
# This teaches the model to interpret spectrogram patterns.

# %%
from peft import LoraConfig, get_peft_model, TaskType, prepare_model_for_kbit_training

# Prepare model for training (freeze base, enable gradients on LoRA)
model = prepare_model_for_kbit_training(model)

# Find target modules — we want attention + MLP in both vision and language
# Print model module names to identify targets
target_modules = []
for name, _ in model.named_modules():
    if any(key in name for key in ["q_proj", "v_proj", "k_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]):
        # Extract just the module type name
        parts = name.split(".")
        if parts[-1] not in target_modules:
            target_modules.append(parts[-1])

target_modules = list(set(target_modules))
print(f"LoRA target modules: {target_modules}")

lora_config = LoraConfig(
    r=8,
    lora_alpha=8,
    lora_dropout=0.0,
    bias="none",
    target_modules=target_modules,
    task_type=TaskType.CAUSAL_LM,
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

# %% [markdown]
# ## 10. Train

# %%
from torch.utils.data import Dataset as TorchDataset, DataLoader
from transformers import TrainingArguments, Trainer

class SpectrogramDataset(TorchDataset):
    """Dataset that tokenizes spectrogram training pairs on-the-fly."""

    def __init__(self, pairs: list[dict]):
        self.pairs = pairs

    def __len__(self) -> int:
        return len(self.pairs)

    def __getitem__(self, idx: int) -> dict:
        pair = self.pairs[idx]
        spec_img = Image.open(pair["spectrogram_path"]).convert("RGB")

        messages = [
            {"role": "user", "content": [
                {"type": "image"},
                {"type": "text", "text": f"{SYSTEM_MSG}\n\n{pair['instruction']}"},
            ]},
            {"role": "assistant", "content": [
                {"type": "text", "text": pair["response"]},
            ]},
        ]

        text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        inputs = processor(text=text, images=[spec_img], return_tensors="pt", padding="max_length", truncation=True, max_length=1024)

        input_ids = inputs["input_ids"].squeeze(0)
        attention_mask = inputs["attention_mask"].squeeze(0)
        labels = input_ids.clone()

        # Mask non-response tokens
        response_tokens = tokenizer.encode(pair["response"], add_special_tokens=False)
        response_len = len(response_tokens)
        if response_len > 0 and len(labels) > response_len:
            labels[:-response_len] = -100

        result = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        }

        # Add pixel values if present
        if "pixel_values" in inputs:
            result["pixel_values"] = inputs["pixel_values"].squeeze(0)

        return result


if audio_files:
    train_dataset = SpectrogramDataset(train_pairs)
    print(f"Training dataset: {len(train_dataset)} examples")
else:
    # Create dummy data
    SPEC_DIR.mkdir(exist_ok=True)
    dummy_pairs = []
    for i in range(10):
        dummy_path = SPEC_DIR / f"dummy_{i}.png"
        if not dummy_path.exists():
            img = Image.fromarray(np.random.randint(0, 255, (SPEC_HEIGHT, SPEC_WIDTH, 3), dtype=np.uint8))
            img.save(str(dummy_path))
        dummy_pairs.append({
            "spectrogram_path": str(dummy_path),
            "instruction": "Classify the breath sounds in this spectrogram. Report JSON.",
            "response": '{"wheeze": false, "crackles": false, "normal": true, "confidence": 0.9, "description": "Normal breath sounds"}',
            "label": "normal",
        })
    train_dataset = SpectrogramDataset(dummy_pairs)
    print("Using dummy data -- add ICBHI dataset for real training")

# %%
training_args = TrainingArguments(
    output_dir="./breath_sound_spectrogram_lora",
    per_device_train_batch_size=1,
    gradient_accumulation_steps=4,
    max_steps=100,
    learning_rate=2e-4,
    fp16=True,
    logging_steps=5,
    save_steps=50,
    save_total_limit=2,
    seed=42,
    report_to="none",
    remove_unused_columns=False,
    dataloader_pin_memory=False,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
)

print("Starting training...")
train_result = trainer.train()
print(f"Training complete")
print(f"  Loss: {train_result.training_loss:.4f}")
print(f"  Steps: {train_result.global_step}")

# %% [markdown]
# ## 11. Save Adapter Weights

# %%
ADAPTER_NAME = "malaika-breath-sounds-spectrogram-lora"

model.save_pretrained(ADAPTER_NAME)
tokenizer.save_pretrained(ADAPTER_NAME)
print(f"Adapter saved to {ADAPTER_NAME}/")

# List adapter files and sizes
for f in sorted(Path(ADAPTER_NAME).glob("*")):
    if f.is_file():
        size_mb = f.stat().st_size / 1024 / 1024
        print(f"  {f.name}: {size_mb:.1f} MB")

# %% [markdown]
# ## 12. Evaluate on Test Set

# %%
print("=" * 60)
print("EVALUATION ON TEST SET")
print("=" * 60)

if audio_files and test_pairs:
    correct = 0
    total_test = 0

    for pair in test_pairs[:20]:  # First 20 for speed
        spec_img = Image.open(pair["spectrogram_path"]).convert("RGB")

        messages = [
            {"role": "user", "content": [
                {"type": "image"},
                {"type": "text", "text": pair["instruction"]},
            ]},
        ]

        input_text = processor.apply_chat_template(messages, add_generation_prompt=True)
        inputs = processor(text=input_text, images=[spec_img], return_tensors="pt").to(model.device)

        with torch.inference_mode():
            outputs = model.generate(**inputs, max_new_tokens=200, do_sample=False)

        new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        prediction = tokenizer.decode(new_tokens, skip_special_tokens=True)

        try:
            json_match = re.search(r'\{[^{}]*\}', prediction)
            if json_match:
                pred_json = json.loads(json_match.group(0))
                expected = json.loads(pair["response"])

                wheeze_match = pred_json.get("wheeze") == expected.get("wheeze")
                crackle_match = pred_json.get("crackles") == expected.get("crackles")

                if wheeze_match and crackle_match:
                    correct += 1
                    status = "PASS"
                else:
                    status = "FAIL"
            else:
                status = "FAIL (no JSON)"
        except (json.JSONDecodeError, KeyError):
            status = "FAIL (parse error)"

        total_test += 1
        print(f"  {status} [{pair['label']}] -- {prediction[:80]}")

    print(f"\nAccuracy: {correct}/{total_test} ({100*correct/total_test:.0f}%)")
else:
    print("No test data available -- add ICBHI dataset to evaluate")

# %% [markdown]
# ## 13. Summary
#
# | Metric | Value |
# |--------|-------|
# | Base model | Gemma 4 E4B (4-bit) |
# | Method | PEFT LoRA, r=8, vision+language |
# | Dataset | ICBHI 2017 (spectrograms) |
# | Input | Mel-spectrogram PNG (512x256, 50-4000 Hz) |
# | Training steps | 100 |
# | Training loss | (see above) |
# | Test accuracy | (see above) |
# | Adapter size | ~50-100MB |
#
# **Innovation**: Audio → spectrogram → vision fine-tuning bypasses Gemma 4's
# lack of native audio support. The mel-spectrogram preserves all acoustic
# features (frequency, intensity, timing) in a visual format that Gemma 4
# can learn to interpret.
#
# **Next**: Download adapter weights and test in the Malaika demo application.
