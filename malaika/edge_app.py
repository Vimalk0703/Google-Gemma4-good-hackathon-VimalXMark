"""Malaika Edge App — fully offline voice IMCI assessment.

100% on-device. Zero internet. Zero cloud calls.
- STT: Whisper-small (244 MB, local)
- Inference: Gemma 4 E4B on local GPU (CUDA/MPS)
- TTS: Piper TTS (offline, 4 languages)

This is a SEPARATE app from voice_app.py. It shares:
- ChatEngine (agentic IMCI flow)
- skills.py (12 clinical skills)
- imci_protocol.py (deterministic WHO classification)
- static/index.html (voice UI)

But it does NOT use:
- Smallest AI (STT/TTS cloud)
- ngrok (tunneling)
- Any external API

Run locally:
    python -m malaika.edge_app

Run on Colab:
    See notebooks/11_edge_offline_colab.ipynb
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Any

import structlog
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from malaika.config import MalaikaConfig, load_config

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# API Models
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    language: str = Field(default="en")


class ChatResponse(BaseModel):
    response: str
    audio_id: str | None = None
    step: str
    events: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Edge App State
# ---------------------------------------------------------------------------


class EdgeAppState:
    """Manages state for the fully offline edge app."""

    def __init__(self, config: MalaikaConfig) -> None:
        self.config = config
        self.session: Any = None
        self.tts: Any = None
        self.whisper: Any = None
        self._audio_cache: dict[str, Path] = {}
        self._temp_dir = Path(tempfile.mkdtemp(prefix="malaika_edge_"))
        logger.info("edge_app_state_initialized", temp_dir=str(self._temp_dir))

    def initialize_session(self, model: Any, processor: Any) -> None:
        """Wire pre-loaded model into ChatEngine."""
        from malaika.chat_engine import ChatEngine

        self.session = ChatEngine(self.config)
        self.session.model = model
        self.session.processor = processor
        self.session.model_loaded = True

        # Initialize offline TTS (Piper)
        try:
            from malaika.tts import MalaikaTTS

            self.tts = MalaikaTTS(self.config)
            if self.tts.available:
                logger.info(
                    "edge_tts_ready", backend="piper", languages=self.tts.supported_languages
                )
            else:
                logger.warning("edge_tts_unavailable", msg="piper-tts not installed")
        except Exception as e:
            logger.warning("edge_tts_init_failed", error=str(e))
            self.tts = None

        # Initialize offline STT (Whisper)
        try:
            from malaika.audio import WhisperTranscriber

            self.whisper = WhisperTranscriber()
            logger.info("edge_stt_ready", backend="whisper-small")
        except Exception as e:
            logger.warning("edge_stt_init_failed", error=str(e))
            self.whisper = None

        logger.info("edge_session_initialized", device=str(model.device))

    def generate_tts(self, text: str, language: str = "en") -> str | None:
        """Generate TTS audio via Piper (offline)."""
        if self.tts is None or not self.tts.available:
            return None
        try:
            wav_path = self.tts.speak(text, language=language)
            if wav_path is None:
                return None
            audio_id = str(uuid.uuid4())[:8]
            self._audio_cache[audio_id] = wav_path
            return audio_id
        except Exception as e:
            logger.error("edge_tts_failed", error=str(e))
            return None

    def get_audio_path(self, audio_id: str) -> Path | None:
        return self._audio_cache.get(audio_id)

    def save_upload(self, content: bytes, suffix: str) -> Path:
        file_path = self._temp_dir / f"{uuid.uuid4().hex[:12]}{suffix}"
        file_path.write_bytes(content)
        return file_path

    def transcribe_audio(self, audio_path: Path) -> str:
        """Transcribe audio via Whisper (offline)."""
        if self.whisper is None:
            raise RuntimeError("Whisper STT not available")
        return self.whisper.transcribe(audio_path)

    def reset_session(self) -> None:
        if self.session is not None:
            self.session.reset()


# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_state: EdgeAppState | None = None

# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Malaika Edge — Fully Offline Child Health AI",
    description="WHO IMCI assessment powered by Gemma 4. Zero internet required.",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def serve_ui() -> HTMLResponse:
    """Serve the voice UI."""
    html_path = Path(__file__).parent / "static" / "index.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="UI not found")
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Process text message (offline)."""
    if _state is None or _state.session is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    result = _state.session.process(user_text=request.text)
    response_text = result["text"]
    audio_id = _state.generate_tts(response_text, language=request.language)

    return ChatResponse(
        response=response_text,
        audio_id=audio_id,
        step=_state.session.step,
        events=result.get("events", []),
    )


@app.post("/api/voice", response_model=ChatResponse)
async def voice_input(
    audio: UploadFile = File(...),
    language: str = Form(default="en"),
) -> ChatResponse:
    """Process voice input via Whisper STT (offline)."""
    if _state is None or _state.session is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    content = await audio.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file")

    suffix = Path(audio.filename or "audio.wav").suffix or ".wav"
    audio_path = _state.save_upload(content, suffix)

    try:
        transcript = _state.transcribe_audio(audio_path)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    if not transcript.strip():
        transcript = "(no speech detected)"

    result = _state.session.process(user_text=transcript)
    response_text = result["text"]
    audio_id = _state.generate_tts(response_text, language=language)

    return ChatResponse(
        response=response_text,
        audio_id=audio_id,
        step=_state.session.step,
        events=result.get("events", []),
    )


@app.post("/api/image", response_model=ChatResponse)
async def image_input(
    image: UploadFile = File(...),
    text: str = Form(default=""),
    language: str = Form(default="en"),
) -> ChatResponse:
    """Process image via Gemma 4 vision (offline)."""
    if _state is None or _state.session is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    content = await image.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty image file")

    suffix = Path(image.filename or "image.jpg").suffix or ".jpg"
    image_path = _state.save_upload(content, suffix)

    result = _state.session.process(user_text=text, image_path=str(image_path))
    response_text = result["text"]
    audio_id = _state.generate_tts(response_text, language=language)

    return ChatResponse(
        response=response_text,
        audio_id=audio_id,
        step=_state.session.step,
        events=result.get("events", []),
    )


@app.get("/api/tts/{audio_id}")
async def get_tts_audio(audio_id: str) -> FileResponse:
    """Retrieve generated Piper TTS audio file."""
    if _state is None:
        raise HTTPException(status_code=503, detail="Not initialized")
    audio_path = _state.get_audio_path(audio_id)
    if audio_path is None or not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio not found")
    return FileResponse(str(audio_path), media_type="audio/wav")


@app.get("/api/mode")
async def get_mode() -> dict[str, Any]:
    """Report that this is the edge (offline) app."""
    return {
        "mode": "edge",
        "internet_required": False,
        "stt": "whisper-small (offline)",
        "tts": "piper (offline)"
        if (_state and _state.tts and _state.tts.available)
        else "disabled",
        "inference": "gemma-4-local",
        "model_loaded": _state is not None
        and _state.session is not None
        and _state.session.model_loaded,
    }


@app.websocket("/api/voice-stream")
async def voice_stream(websocket: WebSocket) -> None:
    """Fully offline voice session — Whisper STT + Piper TTS.

    Same WebSocket protocol as the cloud version, but everything
    runs locally. Zero internet.
    """
    if _state is None or _state.session is None:
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": "Model not loaded"})
        await websocket.close()
        return

    from malaika.chat_engine import ChatEngine
    from malaika.voice_session_edge import EdgeVoiceSessionHandler

    # Fresh ChatEngine per session
    engine = ChatEngine(_state.config)
    engine.model = _state.session.model
    engine.processor = _state.session.processor
    engine.model_loaded = True

    handler = EdgeVoiceSessionHandler(
        websocket,
        engine,
        tts=_state.tts,
        whisper=_state.whisper,
    )
    await handler.run()


@app.post("/api/reset")
async def reset_session() -> dict[str, str]:
    """Reset assessment session."""
    if _state is not None:
        _state.reset_session()
    return {"status": "ok", "message": "Session reset."}


# ---------------------------------------------------------------------------
# Application Factory
# ---------------------------------------------------------------------------


def create_edge_app(
    model: Any,
    processor: Any,
    config: MalaikaConfig | None = None,
) -> FastAPI:
    """Create the fully offline edge app with a pre-loaded model.

    Args:
        model: Loaded Gemma 4 model (Unsloth/Transformers).
        processor: Gemma 4 processor.
        config: Optional config override.

    Returns:
        Configured FastAPI application.
    """
    global _state

    effective_config = config or load_config()
    _state = EdgeAppState(effective_config)
    _state.initialize_session(model, processor)

    # Ensure prompts are registered
    from malaika.prompts import (  # noqa: F401
        PromptRegistry,
        breathing,
        danger_signs,
        diarrhea,
        fever,
        heart,
        nutrition,
        speech,
        system,
        treatment,
    )

    logger.info(
        "edge_app_ready",
        mode="fully_offline",
        prompts=len(PromptRegistry.list_all()),
        tts_available=_state.tts is not None and _state.tts.available,
        stt_available=_state.whisper is not None,
    )

    return app


# ---------------------------------------------------------------------------
# Entry point (local development)
# ---------------------------------------------------------------------------


def main() -> None:
    """Launch the edge app locally."""
    import uvicorn

    config = load_config()
    logger.info("edge_app_starting", mode="fully_offline")

    # Load model locally
    print("Loading Gemma 4 E4B locally...")
    print("This requires a GPU (CUDA) or Apple Silicon (MPS)")

    from malaika.inference import MalaikaInference

    inference = MalaikaInference(config)
    inference.load_model()

    create_edge_app(
        model=inference._model,
        processor=inference._processor,
        config=config,
    )

    print("\nMalaika Edge is running at http://localhost:8000")
    print("Fully offline — zero internet required.\n")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    main()
