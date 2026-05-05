"""Malaika Edge Voice Session — fully offline voice pipeline via WebSocket.

Runs entirely on-device with zero internet:
  Browser mic → PCM audio → Whisper STT (local) → transcript
  → ChatEngine (Gemma 4 local) → response text
  → Piper TTS (local) → audio → Browser speaker

Same WebSocket protocol as voice_session.py but replaces all cloud
services (Smallest AI) with local alternatives:
  - STT: Whisper-small via Transformers (244 MB, offline)
  - TTS: Piper TTS (offline, 4 languages)
  - Inference: Gemma 4 on local GPU (CUDA/MPS)

Trade-offs vs cloud version:
  - Higher latency (Whisper needs full utterance, not streaming)
  - Lower voice quality (Piper vs Smallest AI)
  - But: ZERO internet. Works in a village with no connectivity.

Protocol (browser → server): same as voice_session.py
  {"type": "speech_start"}
  {"type": "speech_end"}
  binary data (PCM16, 16kHz, mono)
  {"type": "text", "text": "..."}
  {"type": "image", "data": "<base64>"}

Protocol (server → browser): same as voice_session.py
  {"type": "state", "state": "..."}
  {"type": "transcript", ...}
  {"type": "audio", "data": "<base64>"}
  {"type": "audio_end"}
  + all agent events (skill_invoked, classification, etc.)
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import struct
import tempfile
from pathlib import Path
from typing import Any

import structlog
from fastapi import WebSocket, WebSocketDisconnect

logger = structlog.get_logger()


class EdgeVoiceSessionHandler:
    """Manages one fully-offline voice session over WebSocket.

    Orchestrates: browser audio → Whisper STT → ChatEngine → Piper TTS → browser.
    Zero cloud calls. Everything runs locally.
    """

    def __init__(
        self,
        websocket: WebSocket,
        chat_engine: Any,
        tts: Any,
        whisper: Any = None,
    ) -> None:
        self.ws = websocket
        self.engine = chat_engine
        self.tts = tts
        self._whisper = whisper
        self.state = "idle"
        self._audio_buffer: bytearray = bytearray()
        self._is_recording = False

    @property
    def whisper(self) -> Any:
        """Lazy-load Whisper transcriber."""
        if self._whisper is None:
            from malaika.audio import WhisperTranscriber

            self._whisper = WhisperTranscriber()
            logger.info("edge_whisper_loaded")
        return self._whisper

    async def run(self) -> None:
        """Main session loop — runs until WebSocket closes."""
        await self.ws.accept()
        await self._send_state("listening")

        # Send initial greeting
        result = self.engine.process(user_text="Hi")
        greeting = result["text"]
        for event in result.get("events", []):
            await self.ws.send_json(event)
        await self._send_transcript("assistant", greeting)
        await self._speak(greeting)
        await self._send_state("listening")

        try:
            while True:
                data = await self.ws.receive()

                if "text" in data:
                    msg = json.loads(data["text"])
                    msg_type = msg.get("type", "")

                    if msg_type == "speech_start":
                        await self._on_speech_start()
                    elif msg_type == "speech_end":
                        await self._on_speech_end()
                    elif msg_type == "text":
                        await self._process_text(msg.get("text", ""))
                    elif msg_type == "image":
                        await self._process_image(msg.get("data", ""))

                elif "bytes" in data:
                    # Buffer PCM audio during recording
                    if self._is_recording:
                        self._audio_buffer.extend(data["bytes"])

        except WebSocketDisconnect:
            logger.info("edge_voice_session_ended")
        except Exception as e:
            logger.error("edge_voice_session_error", error=str(e))
            with contextlib.suppress(Exception):
                await self.ws.send_json({"type": "error", "message": str(e)})

    async def _send_state(self, state: str) -> None:
        """Send state change to browser."""
        self.state = state
        await self.ws.send_json({"type": "state", "state": state})

    async def _send_transcript(self, role: str, text: str) -> None:
        """Send transcript text to browser."""
        await self.ws.send_json({"type": "transcript", "role": role, "text": text})

    async def _send_audio(self, audio_data: bytes) -> None:
        """Send audio chunk to browser as base64."""
        b64 = base64.b64encode(audio_data).decode("ascii")
        await self.ws.send_json({"type": "audio", "data": b64})

    # --- STT: Whisper (offline) ---

    async def _on_speech_start(self) -> None:
        """Start buffering audio from browser mic."""
        self._audio_buffer = bytearray()
        self._is_recording = True
        logger.debug("edge_speech_start")

    async def _on_speech_end(self) -> None:
        """Stop recording, transcribe with Whisper, process result."""
        self._is_recording = False
        audio_data = bytes(self._audio_buffer)
        self._audio_buffer = bytearray()

        if len(audio_data) < 3200:  # < 0.1s at 16kHz
            await self._send_state("listening")
            return

        await self._send_state("thinking")

        # Save PCM to WAV for Whisper
        wav_path = self._pcm_to_wav_file(audio_data, sample_rate=16000)

        # Transcribe with Whisper (blocking — run in thread pool)
        loop = asyncio.get_event_loop()
        try:
            transcript = await loop.run_in_executor(
                None,
                self.whisper.transcribe,
                wav_path,
            )
        except Exception as e:
            logger.error("edge_whisper_failed", error=str(e))
            transcript = ""
        finally:
            wav_path.unlink(missing_ok=True)

        transcript = transcript.strip()
        if transcript:
            await self._process_text(transcript)
        else:
            await self._send_state("listening")

    @staticmethod
    def _pcm_to_wav_file(pcm_data: bytes, sample_rate: int = 16000) -> Path:
        """Convert raw PCM16 bytes to a WAV file for Whisper."""
        with tempfile.NamedTemporaryFile(suffix=".wav", prefix="malaika_edge_", delete=False) as _f:
            tmp = Path(_f.name)
        num_channels = 1
        bits_per_sample = 16
        byte_rate = sample_rate * num_channels * bits_per_sample // 8
        block_align = num_channels * bits_per_sample // 8
        data_size = len(pcm_data)

        with open(tmp, "wb") as f:
            # RIFF header
            f.write(b"RIFF")
            f.write(struct.pack("<I", 36 + data_size))
            f.write(b"WAVE")
            # fmt chunk
            f.write(b"fmt ")
            f.write(struct.pack("<I", 16))  # chunk size
            f.write(struct.pack("<H", 1))  # PCM format
            f.write(struct.pack("<H", num_channels))
            f.write(struct.pack("<I", sample_rate))
            f.write(struct.pack("<I", byte_rate))
            f.write(struct.pack("<H", block_align))
            f.write(struct.pack("<H", bits_per_sample))
            # data chunk
            f.write(b"data")
            f.write(struct.pack("<I", data_size))
            f.write(pcm_data)

        return tmp

    # --- Process + Respond ---

    async def _process_text(self, text: str) -> None:
        """Process user text through ChatEngine and respond with local TTS."""
        if not text:
            return

        await self._send_transcript("user", text)
        await self._send_state("thinking")

        # Run Gemma 4 inference (blocking)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.engine.process,
            text,
            None,
        )

        response_text = result["text"]
        events = result.get("events", [])

        # Send structured events first
        for event in events:
            await self.ws.send_json(event)

        await self._send_transcript("assistant", response_text)

        # Speak via Piper TTS (offline)
        await self._speak(response_text)

        await self._send_state("listening")

    async def _process_image(self, base64_data: str) -> None:
        """Process uploaded image through ChatEngine."""
        image_bytes = base64.b64decode(base64_data)
        with tempfile.NamedTemporaryFile(suffix=".jpg", prefix="malaika_edge_", delete=False) as _f:
            tmp = Path(_f.name)
        tmp.write_bytes(image_bytes)

        await self._send_state("thinking")

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.engine.process,
            "",
            str(tmp),
        )

        response_text = result["text"]
        events = result.get("events", [])

        for event in events:
            await self.ws.send_json(event)

        await self._send_transcript("assistant", response_text)
        await self._speak(response_text)

        tmp.unlink(missing_ok=True)
        await self._send_state("listening")

    # --- TTS: Piper (offline) ---

    async def _speak(self, text: str) -> None:
        """Convert text to speech via Piper TTS (fully offline).

        Piper generates a WAV file. We read it and send as base64 audio.
        """
        await self._send_state("speaking")

        # Clean text for TTS
        clean = (
            text.replace("**", "")
            .replace("##", "")
            .replace("---", "")
            .replace("\n", " ")
            .strip()[:800]
        )

        if not clean or self.tts is None or not self.tts.available:
            await self.ws.send_json({"type": "audio_end"})
            return

        # Generate WAV with Piper (blocking)
        loop = asyncio.get_event_loop()
        wav_path = await loop.run_in_executor(
            None,
            self.tts.speak,
            clean,
            "en",
        )

        if wav_path and wav_path.exists():
            wav_bytes = wav_path.read_bytes()
            await self._send_audio(wav_bytes)
            logger.debug("edge_tts_complete", audio_size=len(wav_bytes))

        await self.ws.send_json({"type": "audio_end"})
