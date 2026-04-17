"""Malaika Voice App — FastAPI server for voice-based IMCI assessment.

Provides REST endpoints for the mobile-first voice UI:
- Text chat with Gemma 4 reasoning
- Voice input via Whisper STT (offline)
- Image analysis via Gemma 4 vision
- Spoken responses via Piper TTS (offline)

All AI inference runs locally. No external API calls.

Run with:
    uvicorn malaika.voice_app:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Any

import structlog
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from malaika.config import MalaikaConfig, load_config

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# API Models (Pydantic)
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    """Text chat message from the caregiver."""

    text: str = Field(..., min_length=1, max_length=2000, description="Caregiver's message")
    language: str = Field(default="en", description="Language code (en, sw, hi, fr)")


class ChatResponse(BaseModel):
    """Malaika's response to the caregiver."""

    response: str = Field(..., description="Malaika's text response")
    audio_id: str | None = Field(default=None, description="TTS audio ID for /api/tts/{id}")
    step: str = Field(..., description="Current IMCI assessment step")
    transcript: str | None = Field(default=None, description="STT transcript (voice input only)")


class SessionStatus(BaseModel):
    """Current assessment session state."""

    step: str = Field(..., description="Current IMCI step name")
    age_months: int = Field(..., description="Child's age in months")
    language: str = Field(..., description="Assessment language")
    model_loaded: bool = Field(..., description="Whether Gemma 4 is loaded")
    findings_count: int = Field(..., description="Number of findings recorded")


class ResetResponse(BaseModel):
    """Response to session reset."""

    status: str = Field(default="ok")
    message: str = Field(default="Session reset. Ready for new assessment.")


# ---------------------------------------------------------------------------
# Application State
# ---------------------------------------------------------------------------


class VoiceAppState:
    """Manages shared state for the voice application.

    Holds references to loaded models, session, and temporary files.
    Thread-safe for single-session demo use.
    """

    def __init__(self, config: MalaikaConfig) -> None:
        self.config = config
        self.session: Any = None
        self.tts: Any = None
        self.whisper: Any = None
        self._audio_cache: dict[str, Path] = {}
        self._temp_dir = Path(tempfile.mkdtemp(prefix="malaika_voice_"))

        logger.info("voice_app_state_initialized", temp_dir=str(self._temp_dir))

    def initialize_session(
        self,
        model: Any,
        processor: Any,
        config: MalaikaConfig | None = None,
    ) -> None:
        """Initialize the chat engine with pre-loaded model and processor.

        Args:
            model: Loaded Gemma 4 model (via Unsloth or Transformers).
            processor: Gemma 4 processor for tokenization and image handling.
            config: Optional config override.
        """
        import torch

        from malaika.chat_engine import ChatEngine

        effective_config = config or self.config
        self.session = ChatEngine(effective_config)
        self.session.model = model
        self.session.processor = processor
        self.session.model_loaded = True

        # Initialize TTS
        try:
            from malaika.tts import MalaikaTTS

            self.tts = MalaikaTTS(effective_config)
            if self.tts.available:
                logger.info("tts_ready", languages=self.tts.supported_languages)
            else:
                logger.warning("tts_unavailable")
        except Exception as e:
            logger.warning("tts_init_failed", error=str(e))
            self.tts = None

        logger.info(
            "session_initialized",
            device=str(model.device),
            vram_gb=f"{torch.cuda.memory_allocated() / 1024**3:.1f}"
            if torch.cuda.is_available()
            else "N/A",
        )

    def generate_tts(self, text: str, language: str = "en") -> str | None:
        """Generate TTS audio and return its cache ID.

        Args:
            text: Text to speak.
            language: Language code (en, sw, hi, fr).

        Returns:
            Audio cache ID string, or None if TTS unavailable.
        """
        if self.tts is None or not self.tts.available:
            return None

        try:
            wav_path = self.tts.speak(text, language=language)
            if wav_path is None:
                return None

            audio_id = str(uuid.uuid4())[:8]
            self._audio_cache[audio_id] = wav_path
            logger.debug("tts_generated", audio_id=audio_id, language=language)
            return audio_id

        except Exception as e:
            logger.error("tts_generation_failed", error=str(e))
            return None

    def get_audio_path(self, audio_id: str) -> Path | None:
        """Retrieve a cached TTS audio file path.

        Args:
            audio_id: Cache ID from generate_tts().

        Returns:
            Path to WAV file, or None if not found.
        """
        return self._audio_cache.get(audio_id)

    def save_upload(self, content: bytes, suffix: str) -> Path:
        """Save uploaded file content to a temporary path.

        Args:
            content: Raw file bytes.
            suffix: File extension (e.g., ".wav", ".jpg").

        Returns:
            Path to saved temporary file.
        """
        file_path = self._temp_dir / f"{uuid.uuid4().hex[:12]}{suffix}"
        file_path.write_bytes(content)
        return file_path

    def transcribe_audio(self, audio_path: Path) -> str:
        """Transcribe audio to text using Whisper STT.

        Args:
            audio_path: Path to audio file (WAV/WebM/MP3).

        Returns:
            Transcribed text string.

        Raises:
            RuntimeError: If Whisper is unavailable.
        """
        if self.whisper is None:
            try:
                from malaika.audio import WhisperTranscriber

                self.whisper = WhisperTranscriber()
            except Exception as e:
                raise RuntimeError(f"Whisper STT unavailable: {e}") from e

        return self.whisper.transcribe(audio_path)

    def reset_session(self) -> None:
        """Reset the assessment session for a new assessment."""
        if self.session is not None:
            self.session.reset()
            logger.info("session_reset")


# ---------------------------------------------------------------------------
# Module-level state (initialized via create_voice_app)
# ---------------------------------------------------------------------------

_state: VoiceAppState | None = None

# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Malaika — Child Health AI",
    description="WHO IMCI child health assessment powered by Gemma 4",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def serve_ui() -> HTMLResponse:
    """Serve the voice UI single-page application."""
    html_path = Path(__file__).parent / "static" / "index.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="UI not found")
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Process a text message from the caregiver.

    Runs the message through the IMCI state machine and returns
    Malaika's conversational response with optional TTS audio.
    """
    if _state is None or _state.session is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    response_text = _state.session.process(user_text=request.text)

    audio_id = _state.generate_tts(response_text, language=request.language)

    logger.info(
        "chat_processed",
        step=_state.session.step,
        text_length=len(request.text),
        response_length=len(response_text),
        has_audio=audio_id is not None,
    )

    return ChatResponse(
        response=response_text,
        audio_id=audio_id,
        step=_state.session.step,
    )


@app.post("/api/voice", response_model=ChatResponse)
async def voice_input(
    audio: UploadFile = File(..., description="Audio recording (WAV/WebM)"),
    language: str = Form(default="en", description="Language code"),
) -> ChatResponse:
    """Process voice input from the caregiver.

    Pipeline: audio file → Whisper STT → text → IMCI processing → response + TTS.
    """
    if _state is None or _state.session is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    # Save uploaded audio
    content = await audio.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file")

    suffix = Path(audio.filename or "audio.wav").suffix or ".wav"
    audio_path = _state.save_upload(content, suffix)

    # Transcribe with Whisper
    try:
        transcript = _state.transcribe_audio(audio_path)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    if not transcript.strip():
        transcript = "(no speech detected)"

    # Process through chat engine
    response_text = _state.session.process(user_text=transcript)

    audio_id = _state.generate_tts(response_text, language=language)

    logger.info(
        "voice_processed",
        step=_state.session.step,
        transcript=transcript[:100],
        response_length=len(response_text),
    )

    return ChatResponse(
        response=response_text,
        audio_id=audio_id,
        step=_state.session.step,
        transcript=transcript,
    )


@app.post("/api/image", response_model=ChatResponse)
async def image_input(
    image: UploadFile = File(..., description="Image file (JPEG/PNG)"),
    text: str = Form(default="", description="Optional text with image"),
    language: str = Form(default="en", description="Language code"),
) -> ChatResponse:
    """Process an image from the caregiver (photo or camera capture).

    The image is analyzed by Gemma 4 vision in the context of the
    current IMCI assessment step.
    """
    if _state is None or _state.session is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    # Validate and save image
    content = await image.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty image file")

    max_size = _state.config.guards.max_image_size_mb * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"Image exceeds {_state.config.guards.max_image_size_mb}MB limit",
        )

    suffix = Path(image.filename or "image.jpg").suffix or ".jpg"
    image_path = _state.save_upload(content, suffix)

    # Process through chat engine with image
    response_text = _state.session.process(
        user_text=text,
        image_path=str(image_path),
    )

    audio_id = _state.generate_tts(response_text, language=language)

    logger.info(
        "image_processed",
        step=_state.session.step,
        image_size_kb=len(content) // 1024,
        response_length=len(response_text),
    )

    return ChatResponse(
        response=response_text,
        audio_id=audio_id,
        step=_state.session.step,
    )


@app.get("/api/tts/{audio_id}")
async def get_tts_audio(audio_id: str) -> FileResponse:
    """Retrieve a generated TTS audio file.

    Args:
        audio_id: Audio cache ID from a chat/voice/image response.

    Returns:
        WAV audio file response.
    """
    if _state is None:
        raise HTTPException(status_code=503, detail="Not initialized")

    audio_path = _state.get_audio_path(audio_id)
    if audio_path is None or not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio not found")

    return FileResponse(
        path=str(audio_path),
        media_type="audio/wav",
        filename=f"malaika_{audio_id}.wav",
    )


@app.get("/api/status", response_model=SessionStatus)
async def get_status() -> SessionStatus:
    """Get current assessment session status."""
    if _state is None or _state.session is None:
        raise HTTPException(status_code=503, detail="Not initialized")

    session = _state.session
    findings_count = sum(
        1
        for v in session.findings.values()
        if v and v != 0
    )

    return SessionStatus(
        step=session.step,
        age_months=session.age_months,
        language=session.language,
        model_loaded=session.model_loaded,
        findings_count=findings_count,
    )


@app.post("/api/reset", response_model=ResetResponse)
async def reset_session() -> ResetResponse:
    """Reset the assessment session for a new assessment."""
    if _state is None:
        raise HTTPException(status_code=503, detail="Not initialized")

    _state.reset_session()
    return ResetResponse()


# ---------------------------------------------------------------------------
# Application Factory
# ---------------------------------------------------------------------------


def create_voice_app(
    model: Any,
    processor: Any,
    config: MalaikaConfig | None = None,
) -> FastAPI:
    """Create and configure the voice application with a pre-loaded model.

    Args:
        model: Loaded Gemma 4 model (via Unsloth).
        processor: Gemma 4 processor for tokenization.
        config: Optional MalaikaConfig override.

    Returns:
        Configured FastAPI application instance.
    """
    global _state  # noqa: PLW0603

    effective_config = config or load_config()
    _state = VoiceAppState(effective_config)
    _state.initialize_session(model, processor, effective_config)

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
        "voice_app_ready",
        prompts=len(PromptRegistry.list_all()),
        tts_available=_state.tts is not None and _state.tts.available,
    )

    return app
