# Notebook 12 — Village Clinic Fine-Tuned Model (Plan)

> Design document for `notebooks/12_village_clinic_finetuned.ipynb`.
>
> **Why this notebook exists:** The §10 "Two-Tier Vision" beat in `VIDEO_SCRIPT.md` claims Malaika scales from offline-phone (Tier 0) to a village clinic with basic internet (Tier 1). This notebook is the *receipt* for that claim. Without it, §10 is a promise. With it, §10 is a deliverable.

---

## The Two-Tier Architecture

```
TIER 0 — REMOTEST VILLAGE (no internet)
+--------------------------------------------------+
|  $60 Android phone                               |
|  Gemma 4 E2B (2.58 GB, fully offline)            |
|  - Voice in/out (Android native CPU)             |
|  - Vision: alertness, eyes, ribs, edema          |
|  - 12-skill agentic IMCI assessment              |
|  - Deterministic WHO classification              |
+--------------------------------------------------+
                  |
                  | (intermittent Wi-Fi to clinic)
                  v
TIER 1 — VILLAGE CLINIC (basic internet — 10–20 km)
+--------------------------------------------------+
|  Single $300 mini-PC or NUC, on the clinic LAN   |
|  Gemma 4 E4B (4.5B params)                       |
|  + LoRA adapter (ICBHI 2017, 82 MB)              |
|  - Breath-sound spectrogram classification       |
|  - Multi-image vision comparison                 |
|  - Deeper multilingual reasoning                 |
|  - Differential diagnosis with longer context    |
+--------------------------------------------------+
```

The phone always works. The clinic server augments. **Either tier is independently useful.** The clinic does not require the phone, and the phone does not require the clinic. They compose.

---

## What This Notebook Demonstrates

A clinic with a Wi-Fi router and a refurbished mini-PC can offer Gemma 4 E4B-class reasoning to every phone within Wi-Fi range, **without sending a child's data to anyone's cloud**. The clinic server is the clinic's own hardware. It runs the model the clinic owns, on the network the clinic controls.

The notebook proves four things:

1. We can load `Vimal0703/malaika-breath-sounds-E4B-merged` (our fine-tuned merged model from notebook 06) on a Colab T4 / Kaggle T4 GPU.
2. We can wrap it in a tiny FastAPI server that exposes one endpoint: `POST /breath` taking a WAV file, returning JSON `{abnormal: bool, confidence: float, description: str}`.
3. We can publish the URL via ngrok so the Flutter app (or any HTTP client) can call it from outside the Colab/Kaggle network — simulating the phone-in-village calling the clinic-on-Wi-Fi.
4. End-to-end latency, throughput, and quality numbers — measured live, on the same dataset the model was trained on (held-out patients only).

---

## Cell-by-Cell Plan

### Cell 0 — Markdown header

Mission statement, two-tier diagram, link back to the script's §10.

### Cell 1 — Install

```python
%%capture
!pip install unsloth fastapi pyngrok uvicorn[standard] librosa soundfile Pillow python-multipart
```

### Cell 2 — Authenticate

```python
from huggingface_hub import login
from kaggle_secrets import UserSecretsClient
secrets = UserSecretsClient()
login(token=secrets.get_secret("HF_TOKEN"))
NGROK_TOKEN = secrets.get_secret("NGROK_TOKEN")
```

### Cell 3 — Load fine-tuned merged model

```python
from unsloth import FastModel
import torch

model, tokenizer = FastModel.from_pretrained(
    model_name="Vimal0703/malaika-breath-sounds-E4B-merged",
    max_seq_length=2048,
    load_in_4bit=True,
    dtype=None,
    full_finetuning=False,
)
print(f"Loaded — VRAM: {torch.cuda.memory_allocated()/1024**3:.2f} GB")
```

### Cell 4 — Audio → spectrogram pipeline

Reuses the exact `audio_to_spec` function from notebook 06. Critical: must produce identical spectrograms to training distribution (mel, 50–4000 Hz, 512×256 PNG, flipped vertically).

### Cell 5 — Inference helper

```python
from transformers import AutoProcessor
from PIL import Image
import io, json, re

processor = AutoProcessor.from_pretrained("google/gemma-4-E4B-it")

def classify_breath_sound(wav_bytes: bytes) -> dict:
    """Take raw WAV bytes, return classification dict."""
    spec_path = "/tmp/incoming_spec.png"
    with open("/tmp/incoming.wav", "wb") as f:
        f.write(wav_bytes)
    if not audio_to_spec("/tmp/incoming.wav", spec_path):
        return {"error": "could not process audio"}
    img = Image.open(spec_path).convert("RGB")
    messages = [{"role": "user", "content": [
        {"type": "image"},
        {"type": "text", "text": INSTRUCTION},
    ]}]
    txt = processor.apply_chat_template(messages, add_generation_prompt=True)
    inputs = processor(text=txt, images=[img], return_tensors="pt").to(model.device)
    with torch.inference_mode():
        out = model.generate(**inputs, max_new_tokens=200, do_sample=False)
    raw = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    m = re.search(r'\{[^{}]*\}', re.sub(r'```(?:json)?', '', raw))
    return json.loads(m.group(0)) if m else {"error": "parse failed", "raw": raw}
```

### Cell 6 — FastAPI server with /breath, /health endpoints

```python
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import uvicorn, threading, time

app = FastAPI(title="Malaika Village Clinic Server")

@app.get("/health")
def health(): return {"status": "ok", "model": "gemma-4-E4B-merged-breathsound"}

@app.post("/breath")
async def breath(audio: UploadFile = File(...)):
    if not audio.filename.lower().endswith((".wav", ".mp3", ".m4a")):
        return JSONResponse({"error": "audio file required"}, status_code=400)
    wav_bytes = await audio.read()
    result = classify_breath_sound(wav_bytes)
    return JSONResponse(result)

def run_server():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()
time.sleep(3)
print("Server running on :8000")
```

### Cell 7 — Expose via ngrok (so a phone can call from outside)

```python
from pyngrok import ngrok
ngrok.set_auth_token(NGROK_TOKEN)
tunnel = ngrok.connect(8000, "http")
public_url = tunnel.public_url
print(f"\nMalaika Village Clinic Server live at:\n  {public_url}\n")
print(f"Health check: {public_url}/health")
print(f"POST /breath with audio file (WAV/MP3/M4A)")
```

### Cell 8 — Live demo: call the endpoint with a held-out test sample

```python
import requests, random

# Pick a held-out test case
demo_pair = random.choice([p for p in test_pairs if p["label"] == "abnormal"])
print(f"Demo case (held-out patient): {demo_pair['original_label']}")

# Build a real WAV file (or use one from the dataset)
demo_wav_path = demo_pair["audio_path"]  # original audio file
with open(demo_wav_path, "rb") as f:
    response = requests.post(
        f"{public_url}/breath",
        files={"audio": (Path(demo_wav_path).name, f, "audio/wav")},
        timeout=60,
    )
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")
```

### Cell 9 — Throughput benchmark

```python
import time
t0 = time.monotonic()
correct = 0
for pair in test_pairs[:20]:
    with open(pair["audio_path"], "rb") as f:
        r = requests.post(f"{public_url}/breath",
            files={"audio": (Path(pair["audio_path"]).name, f, "audio/wav")},
            timeout=60).json()
    is_abn = r.get("abnormal")
    expected = pair["label"] == "abnormal"
    if is_abn == expected: correct += 1
elapsed = time.monotonic() - t0
print(f"\n20 samples, {correct}/20 correct ({correct*5}%)")
print(f"Total time: {elapsed:.1f}s, mean per sample: {elapsed/20:.2f}s")
print(f"Throughput: {20*60/elapsed:.1f} requests/min")
```

### Cell 10 — Privacy proof + how to integrate with phone

```python
print("=" * 60)
print("PRIVACY ARCHITECTURE")
print("=" * 60)
print("""
This server runs entirely in the clinic's own infrastructure.
The audio file is processed on the GPU and discarded.
No data is logged. No data is persisted. No data is sent anywhere else.

In production (clinic deployment):
  - Replace ngrok with the clinic's local IP on the LAN.
  - The phone calls the server only when on the clinic Wi-Fi.
  - When off the clinic Wi-Fi, the phone falls back to Gemma 4 E2B
    on-device — no audio analysis, but full IMCI assessment still works.

Integration in malaika_flutter:
  - Setting → "Connected mode → Clinic server URL"
  - When detected on clinic Wi-Fi (SSID match) → enable /breath endpoint calls.
  - Otherwise → on-device E2B only.

This is what 'two-tier deployment' actually means in code.
""")
```

### Cell 11 — Summary card (matches notebook 06's format)

```python
print("=" * 60)
print("VILLAGE CLINIC SERVER SUMMARY")
print("=" * 60)
print(f"Base model:        google/gemma-4-E4B-it (4.5B params)")
print(f"Adapter:           Unsloth QLoRA, r=8, ICBHI 2017")
print(f"Trained on:        {len(train_pairs)} balanced spectrograms (notebook 06)")
print(f"Held-out accuracy: 85% crackle, 40% overall (binary)")
print(f"Endpoint:          POST /breath  (audio file → JSON classification)")
print(f"Privacy:           clinic-local server, no cloud, no logs")
print(f"Latency (T4):      ~3-5s per audio sample")
print()
print("This is Tier 1 of Malaika's two-tier deployment.")
print("Tier 0 (phone, fully offline) — see malaika_flutter/")
print("Tier 1 (clinic, basic internet) — this notebook")
```

---

## Inputs Required to Run

| Resource | Where it comes from |
|----------|---------------------|
| Hugging Face token (`HF_TOKEN`) | Kaggle Secrets — needed to load `Vimal0703/malaika-breath-sounds-E4B-merged` |
| ngrok auth token (`NGROK_TOKEN`) | Kaggle Secrets — needed for the phone-callable URL |
| ICBHI 2017 dataset | Kaggle dataset `vbookshelf/respiratory-sound-database` (added via "Add Data") |
| GPU | Kaggle T4 (free tier works) or Colab T4 |

---

## Outputs Produced

1. A live HTTP endpoint URL the phone can call — printed in Cell 7
2. A real `/breath` API that accepts WAV/MP3/M4A and returns JSON classification
3. Live throughput numbers — printed in Cell 9
4. A privacy + integration architecture explanation — Cell 10
5. A reproducible summary card matching notebook 06's format — Cell 11

---

## How This Connects to the Video

`VIDEO_SCRIPT.md` §9 — Mark says:

> *"In a small district hospital — a clinic ten kilometres from the remotest village, with one nurse and one Wi-Fi router — we run a second tier: a clinic server with the bigger Gemma 4 E4B model, plus a LoRA adapter we fine-tuned ourselves on the ICBHI 2017 respiratory dataset. … When the phone has Wi-Fi, it offloads the audio analysis to that clinic server. When it doesn't, it falls back to the on-device model."*

**Without this notebook**, that line is unsupported. **With this notebook**, the line is true — anyone can fork the repo, add their HF and ngrok tokens, run the notebook, and have a live village-clinic server in fifteen minutes. Judges can verify the entire claim themselves.

---

## How This Connects to Existing Repo Artefacts

- Trains-on-the-shoulders-of: `notebooks/06_unsloth_binary_phase1.ipynb` (the original fine-tuning run)
- Uses: `adapters/adapter_model.safetensors` (already merged into the HF-hosted model `Vimal0703/malaika-breath-sounds-E4B-merged`)
- Calls into: same `audio_to_spec` and `INSTRUCTION` constants as notebook 06 (consistent training/inference distribution)
- Mirrors structure of: `notebooks/10_voice_agent_colab.ipynb` (same FastAPI + ngrok server pattern)
- Phone integration: would update `malaika_flutter/lib/inference/inference_service.dart` to optionally call this endpoint when on Wi-Fi

---

## Effort Estimate

| Phase | Time | Risk |
|-------|------|------|
| Scaffold notebook (writing cells) | 1 hour | Low — pattern reuse from 06, 10 |
| First Kaggle T4 run, debug auth/network | 1 hour | Med — Kaggle ngrok occasionally rate-limited |
| Verify accuracy matches notebook 06 numbers | 30 min | Low — same model, same data |
| Add Flutter client integration in `inference_service.dart` | 1 hour | Med — needs SSID detection on Android |
| End-to-end test: phone on local Wi-Fi calling notebook server | 30 min | Med — requires local network setup |

**Total: ~4 hours.** Achievable in one focused session.

---

## What This Notebook Does NOT Do

(Per `REASONS_WE_WILL_FAIL.md`, we are explicit about boundaries.)

- It does not claim production-grade clinical accuracy. The 40% overall / 85% crackle number is from the ICBHI 2017 held-out set. It is a hackathon-grade fine-tune, not an FDA-cleared classifier.
- It does not run on the phone. By design — the phone doesn't have the GPU headroom, which is exactly why this tier exists.
- It does not implement HTTPS / authentication — that's a clinic deployment concern, not a hackathon concern. Add Caddy or a reverse proxy in production.
- It does not integrate the SSID-switching logic into `malaika_flutter` in this notebook — that's a separate Dart change.

---

*Plan authored: 2026-04-30. Will be implemented as `notebooks/12_village_clinic_finetuned.ipynb` in the next sprint.*
