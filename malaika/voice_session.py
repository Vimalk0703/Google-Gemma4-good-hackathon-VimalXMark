"""Malaika Voice Session — real-time voice pipeline via WebSocket.

Handles the full voice interaction loop:
  Browser mic → PCM audio → Smallest AI STT → transcript
  → ChatEngine (Gemma 4) → response text
  → Smallest AI TTS → audio → Browser speaker

Single WebSocket connection between browser and server.
Server handles all Smallest AI communication (auth headers).

Protocol (browser → server):
  {"type": "speech_start"}          — user started speaking
  {"type": "speech_end"}            — user stopped speaking
  binary data                       — PCM16 audio chunks (16kHz, mono)

Protocol (server → browser):
  {"type": "state", "state": "..."}           — listening/thinking/speaking
  {"type": "transcript", "text": "...", "role": "user"}
  {"type": "transcript", "text": "...", "role": "assistant"}
  {"type": "audio", "data": "<base64>"}       — TTS audio chunk
  {"type": "audio_end"}                        — TTS playback complete
  {"type": "error", "message": "..."}
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import random
import re
from typing import Any

import structlog
import websockets
from fastapi import WebSocket, WebSocketDisconnect

logger = structlog.get_logger()

# Smallest AI endpoints
PULSE_STT_URL = "wss://waves-api.smallest.ai/api/v1/pulse/get_text"
WAVES_TTS_URL = "https://waves-api.smallest.ai/api/v1/lightning-v3.1/get_speech"

# Sentence boundary regex for TTS streaming
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")

# Filler phrases for dead air prevention during thinking
_FILLER_PHRASES = [
    "Let me think about that.",
    "Okay, one moment.",
    "Let me check on that.",
    "Let me look at that.",
]

# Filler phrases specifically for image analysis
_IMAGE_FILLER_PHRASES = [
    "Let me look at that photo carefully.",
    "I am analyzing the photo now.",
    "One moment while I examine this.",
]


class VoiceSessionHandler:
    """Manages one real-time voice session over WebSocket.

    Orchestrates: browser audio → STT → AI → TTS → browser playback.
    """

    def __init__(
        self,
        websocket: WebSocket,
        chat_engine: Any,
        api_key: str,
    ) -> None:
        self.ws = websocket
        self.engine = chat_engine
        self.api_key = api_key
        self.stt_ws: Any = None
        self.state = "idle"
        self._transcript_buffer = ""

    def _is_stt_closed(self) -> bool:
        """Check if STT WebSocket is closed (compatible with websockets v13+)."""
        if self.stt_ws is None:
            return True
        try:
            # websockets v15+
            if hasattr(self.stt_ws, "protocol"):
                return self.stt_ws.protocol.state != 1
            # websockets v13-14
            if hasattr(self.stt_ws, "closed"):
                return self.stt_ws.closed
            return False
        except Exception:
            return True

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

        # Pre-warm STT connection
        await self._connect_stt()

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
                        # Text input (typed message)
                        await self._process_text(msg.get("text", ""))
                    elif msg_type == "image":
                        # Image input (base64)
                        await self._process_image(msg.get("data", ""))

                elif "bytes" in data:
                    # Raw PCM audio from browser mic
                    await self._feed_audio(data["bytes"])

        except WebSocketDisconnect:
            logger.info("voice_session_ended")
        except Exception as e:
            logger.error("voice_session_error", error=str(e))
            with contextlib.suppress(Exception):
                await self._send_error(str(e))
        finally:
            await self._cleanup()

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

    async def _send_error(self, message: str) -> None:
        """Send error to browser."""
        await self.ws.send_json({"type": "error", "message": message})

    # --- STT Pipeline ---

    async def _connect_stt(self) -> None:
        """Connect to Smallest AI Pulse STT."""
        if not self.api_key:
            logger.debug("stt_skipped_no_key")
            return
        try:
            url = f"{PULSE_STT_URL}?language=en&sample_rate=16000&encoding=linear16"
            self.stt_ws = await websockets.connect(
                url,
                additional_headers={"Authorization": f"Bearer {self.api_key}"},
            )
            logger.info("stt_connected")
        except Exception as e:
            logger.error("stt_connect_failed", error=str(e))
            self.stt_ws = None

    async def _on_speech_start(self) -> None:
        """Handle speech start from browser VAD."""
        logger.info("speech_start_received")
        self._transcript_buffer = ""
        if self.stt_ws is None or self._is_stt_closed():
            await self._connect_stt()

        # Start reading STT responses in background
        if self.stt_ws:
            asyncio.create_task(self._read_stt())
        else:
            logger.error("stt_not_available_for_speech")

    _audio_chunks_sent: int = 0

    async def _feed_audio(self, pcm_data: bytes) -> None:
        """Forward PCM audio to Smallest AI STT."""
        if self.stt_ws and not self._is_stt_closed():
            try:
                await self.stt_ws.send(pcm_data)
                self._audio_chunks_sent += 1
                if self._audio_chunks_sent % 20 == 0:
                    logger.debug(
                        "audio_streaming", chunks=self._audio_chunks_sent, bytes=len(pcm_data)
                    )
            except Exception as e:
                logger.error("audio_send_failed", error=str(e))

    async def _on_speech_end(self) -> None:
        """Handle speech end — finalize STT and process."""
        if self.stt_ws and not self._is_stt_closed():
            try:
                await self.stt_ws.send(json.dumps({"type": "end"}))
                # Wait briefly for final transcript
                await asyncio.sleep(1.0)
            except Exception:
                pass

        # Close STT connection (Pulse requires fresh connection per utterance)
        if self.stt_ws:
            with contextlib.suppress(Exception):
                await self.stt_ws.close()
            self.stt_ws = None

        # Process the accumulated transcript
        transcript = self._transcript_buffer.strip()
        if transcript:
            await self._process_text(transcript)
        else:
            # No transcript — go back to listening
            await self._connect_stt()
            await self._send_state("listening")

    async def _read_stt(self) -> None:
        """Read transcriptions from Smallest AI STT."""
        if not self.stt_ws:
            return

        try:
            while True:
                try:
                    message = await asyncio.wait_for(self.stt_ws.recv(), timeout=30.0)
                except TimeoutError:
                    break

                if isinstance(message, bytes):
                    message = message.decode("utf-8")

                try:
                    data = json.loads(message)
                    text = data.get("transcript") or data.get("text") or ""
                    is_final = data.get("is_final", False)

                    if text:
                        if is_final:
                            self._transcript_buffer += " " + text
                        display = (self._transcript_buffer + " " + text).strip()
                        await self._send_transcript("user", display)

                except json.JSONDecodeError:
                    pass

        except Exception as e:
            logger.debug("stt_read_ended", error=str(e))

    # --- Process + Respond ---

    async def _process_text(self, text: str) -> None:
        """Process user text through ChatEngine and respond with voice."""
        if not text:
            return

        await self._send_transcript("user", text)
        await self._send_state("thinking")

        # Start filler audio concurrently (plays after 1.5s if still thinking)
        filler_task = asyncio.create_task(self._send_filler())

        # Run Gemma 4 inference (blocking — runs in thread pool)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.engine.process,
            text,
            None,
        )

        # Cancel filler if it hasn't played yet
        filler_task.cancel()

        response_text = result["text"]
        events = result.get("events", [])

        # Send structured events BEFORE transcript (UI updates first)
        for event in events:
            await self.ws.send_json(event)

        await self._send_transcript("assistant", response_text)

        # Speak the response with sentence-level streaming
        await self._speak(response_text)

        # Re-connect STT and go back to listening
        await self._connect_stt()
        await self._send_state("listening")

    async def _process_image(self, base64_data: str) -> None:
        """Process uploaded image through ChatEngine."""
        import tempfile
        from pathlib import Path

        # Decode and save image
        image_bytes = base64.b64decode(base64_data)
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        tmp.write(image_bytes)
        tmp.close()

        await self._send_state("thinking")

        # Image analysis filler (more specific)
        filler_task = asyncio.create_task(self._send_filler(_IMAGE_FILLER_PHRASES))

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.engine.process,
            "",
            tmp.name,
        )

        filler_task.cancel()

        response_text = result["text"]
        events = result.get("events", [])

        for event in events:
            await self.ws.send_json(event)

        await self._send_transcript("assistant", response_text)
        await self._speak(response_text)

        # Cleanup
        Path(tmp.name).unlink(missing_ok=True)

        await self._connect_stt()
        await self._send_state("listening")

    # --- TTS (Sentence-Level Streaming) ---

    async def _speak(self, text: str) -> None:
        """Convert text to speech with sentence-level streaming.

        Splits the response into sentences and TTS each independently.
        The browser receives multiple audio chunks for smooth playback.
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

        if not clean:
            return

        # Split into sentences and merge short fragments
        sentences = _SENTENCE_BOUNDARY.split(clean)
        merged: list[str] = []
        current = ""
        for s in sentences:
            s = s.strip()
            if not s:
                continue
            if len(current) + len(s) + 1 < 80:
                current = (current + " " + s).strip()
            else:
                if current:
                    merged.append(current)
                current = s
        if current:
            merged.append(current)

        if not merged:
            merged = [clean]

        # TTS each sentence independently for low-latency streaming
        for sentence in merged:
            if len(sentence) < 10:
                continue
            try:
                await self._tts_sentence(sentence)
            except Exception as e:
                logger.error("tts_sentence_failed", error=str(e), sentence=sentence[:50])

        await self.ws.send_json({"type": "audio_end"})

    async def _tts_sentence(self, sentence: str) -> None:
        """TTS a single sentence and send audio to browser."""
        if not self.api_key:
            return  # No TTS without API key — transcript is still shown
        import httpx

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                WAVES_TTS_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "text": sentence,
                    "voice_id": "sophia",
                    "sample_rate": 24000,
                    "speed": 1.0,
                    "add_wav_header": True,
                },
            )
            response.raise_for_status()

        await self._send_audio(response.content)
        logger.debug("tts_sentence", length=len(sentence), audio_size=len(response.content))

    async def _send_filler(
        self,
        phrases: list[str] | None = None,
    ) -> None:
        """Send filler audio after a delay to prevent dead air during thinking.

        Only plays if the main inference takes longer than 1.5 seconds.
        Cancelled by the caller if inference completes first.
        """
        await asyncio.sleep(1.5)
        phrase = random.choice(phrases or _FILLER_PHRASES)
        try:
            await self._send_state("speaking")
            await self._tts_sentence(phrase)
            await self._send_state("thinking")
        except asyncio.CancelledError:
            raise
        except Exception:
            pass  # Filler is best-effort

    # --- Cleanup ---

    async def _cleanup(self) -> None:
        """Clean up connections."""
        if self.stt_ws and not self._is_stt_closed():
            with contextlib.suppress(Exception):
                await self.stt_ws.close()
        self.stt_ws = None
