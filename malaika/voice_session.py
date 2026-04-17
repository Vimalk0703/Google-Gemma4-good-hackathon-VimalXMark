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
import json
import os
from typing import Any

import structlog
import websockets
from fastapi import WebSocket, WebSocketDisconnect

logger = structlog.get_logger()

# Smallest AI endpoints
PULSE_STT_URL = "wss://waves-api.smallest.ai/api/v1/pulse/get_text"
WAVES_TTS_URL = "https://waves-api.smallest.ai/api/v1/lightning-v3.1/get_speech"


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

    async def run(self) -> None:
        """Main session loop — runs until WebSocket closes."""
        await self.ws.accept()
        await self._send_state("listening")

        # Send initial greeting
        greeting = self.engine.process(user_text="Hi")
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
            try:
                await self._send_error(str(e))
            except Exception:
                pass
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
        self._transcript_buffer = ""
        if self.stt_ws is None or self.stt_ws.closed:
            await self._connect_stt()

        # Start reading STT responses in background
        if self.stt_ws:
            asyncio.create_task(self._read_stt())

    async def _feed_audio(self, pcm_data: bytes) -> None:
        """Forward PCM audio to Smallest AI STT."""
        if self.stt_ws and not self.stt_ws.closed:
            try:
                await self.stt_ws.send(pcm_data)
            except Exception:
                pass

    async def _on_speech_end(self) -> None:
        """Handle speech end — finalize STT and process."""
        if self.stt_ws and not self.stt_ws.closed:
            try:
                await self.stt_ws.send(json.dumps({"type": "end"}))
                # Wait briefly for final transcript
                await asyncio.sleep(1.0)
            except Exception:
                pass

        # Close STT connection (Pulse requires fresh connection per utterance)
        if self.stt_ws:
            try:
                await self.stt_ws.close()
            except Exception:
                pass
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
            async for message in self.stt_ws:
                if isinstance(message, bytes):
                    message = message.decode("utf-8")

                try:
                    data = json.loads(message)
                    text = data.get("transcript") or data.get("text") or ""
                    is_final = data.get("is_final", False)

                    if text:
                        if is_final:
                            self._transcript_buffer += " " + text
                        # Send interim transcript to browser
                        display = (self._transcript_buffer + " " + text).strip()
                        await self._send_transcript("user", display)

                except json.JSONDecodeError:
                    pass

        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            logger.debug("stt_read_error", error=str(e))

    # --- Process + Respond ---

    async def _process_text(self, text: str) -> None:
        """Process user text through ChatEngine and respond with voice."""
        if not text:
            return

        await self._send_transcript("user", text)
        await self._send_state("thinking")

        # Run Gemma 4 inference (blocking — runs in thread pool)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, self.engine.process, text, None,
        )

        await self._send_transcript("assistant", response)

        # Speak the response
        await self._speak(response)

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

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, self.engine.process, "", tmp.name,
        )

        await self._send_transcript("assistant", response)
        await self._speak(response)

        # Cleanup
        Path(tmp.name).unlink(missing_ok=True)

        await self._connect_stt()
        await self._send_state("listening")

    # --- TTS ---

    async def _speak(self, text: str) -> None:
        """Convert text to speech via Smallest AI TTS and send to browser."""
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

        try:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    WAVES_TTS_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "text": clean,
                        "voice_id": "sophia",
                        "sample_rate": 24000,
                        "speed": 1.0,
                        "add_wav_header": True,
                    },
                )
                response.raise_for_status()

            # Send audio to browser
            await self._send_audio(response.content)
            await self.ws.send_json({"type": "audio_end"})

            logger.info("tts_complete", text_length=len(clean), audio_size=len(response.content))

        except Exception as e:
            logger.error("tts_failed", error=str(e))
            # Continue without audio — text transcript is already shown

    # --- Cleanup ---

    async def _cleanup(self) -> None:
        """Clean up connections."""
        if self.stt_ws and not self.stt_ws.closed:
            try:
                await self.stt_ws.close()
            except Exception:
                pass
        self.stt_ws = None
