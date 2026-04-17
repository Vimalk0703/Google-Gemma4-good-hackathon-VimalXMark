#!/usr/bin/env python3
"""Run Malaika Edge locally on Mac (MPS) or Linux (CUDA).

Access from your iPhone via local WiFi — zero internet needed.

Usage:
    # 1. Start on your Mac:
    python scripts/run_edge_local.py

    # 2. Open on your iPhone (same WiFi):
    #    http://<your-mac-ip>:8000

    # 3. For video demo:
    #    - Put Mac in airplane mode
    #    - Create iPhone hotspot OR use local-only WiFi
    #    - Both devices on same network, zero internet
    #    - Full Malaika experience works

Requirements:
    - Mac with Apple Silicon (M1/M2/M3/M4) OR Linux with CUDA GPU
    - Python 3.11+
    - pip install -r requirements.txt
    - pip install piper-tts  (for offline TTS)
"""

import os
import sys
import socket
import time

# Ensure we're in the project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
os.chdir(project_root)


def get_local_ip() -> str:
    """Get the Mac's local IP address for iPhone access."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


def main() -> None:
    import torch

    print("=" * 60)
    print("  MALAIKA EDGE — Fully Offline Setup")
    print("=" * 60)

    # Detect device
    if torch.cuda.is_available():
        device = "cuda"
        vram = f"{torch.cuda.get_device_properties(0).total_mem / 1024**3:.1f} GB"
        print(f"\n  GPU: {torch.cuda.get_device_name(0)} ({vram})")
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = "mps"
        print(f"\n  GPU: Apple Silicon (MPS)")
    else:
        device = "cpu"
        print(f"\n  WARNING: No GPU found. Will be slow on CPU.")

    # Load model
    print(f"\n  Loading Gemma 4 E4B on {device}...")
    print("  (First run downloads ~5GB. After that, it loads from cache.)")
    t0 = time.time()

    from malaika.config import load_config
    config = load_config()

    # Try Unsloth first (better for MPS/CUDA), fall back to Transformers
    model = None
    processor = None

    try:
        from unsloth import FastModel
        model, _tokenizer = FastModel.from_pretrained(
            model_name="unsloth/gemma-4-E4B-it",
            max_seq_length=2048,
            load_in_4bit=True,
            dtype=None,
            full_finetuning=False,
        )
        from transformers import AutoProcessor
        processor = AutoProcessor.from_pretrained("google/gemma-4-E4B-it")
        print(f"  Loaded via Unsloth in {time.time()-t0:.0f}s")
    except Exception as e:
        print(f"  Unsloth not available ({e}), trying Transformers...")
        from transformers import AutoModelForCausalLM, AutoProcessor
        model = AutoModelForCausalLM.from_pretrained(
            "google/gemma-4-E4B-it",
            device_map="auto",
            torch_dtype=torch.bfloat16,
        )
        processor = AutoProcessor.from_pretrained("google/gemma-4-E4B-it")
        print(f"  Loaded via Transformers in {time.time()-t0:.0f}s")

    if torch.cuda.is_available():
        print(f"  VRAM used: {torch.cuda.memory_allocated()/1024**3:.1f} GB")

    # Create edge app
    from malaika.edge_app import create_edge_app
    app = create_edge_app(model=model, processor=processor, config=config)

    # Get local IP
    local_ip = get_local_ip()
    PORT = 8000

    print(f"\n{'=' * 60}")
    print(f"  MALAIKA EDGE IS READY")
    print(f"{'=' * 60}")
    print(f"\n  On this Mac:  http://localhost:{PORT}")
    print(f"  On iPhone:    http://{local_ip}:{PORT}")
    print(f"\n  How to access from iPhone:")
    print(f"  1. Connect iPhone to same WiFi as this Mac")
    print(f"  2. Open Safari: http://{local_ip}:{PORT}")
    print(f"  3. Tap the orb to start")
    print(f"\n  For video demo (airplane mode proof):")
    print(f"  1. Create iPhone hotspot (Settings > Personal Hotspot)")
    print(f"  2. Connect Mac to iPhone hotspot")
    print(f"  3. Put BOTH in airplane mode (hotspot still works)")
    print(f"  4. Open http://{local_ip}:{PORT} on iPhone Safari")
    print(f"  5. Full Malaika works — zero internet!")
    print(f"\n  Components:")
    print(f"  - Inference: Gemma 4 E4B on {device}")
    print(f"  - STT:       Whisper-small (local)")
    print(f"  - TTS:       Piper (local)")
    print(f"  - Internet:  NOT NEEDED")
    print(f"\n{'=' * 60}")
    print(f"  Press Ctrl+C to stop")
    print(f"{'=' * 60}\n")

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")


if __name__ == "__main__":
    main()
