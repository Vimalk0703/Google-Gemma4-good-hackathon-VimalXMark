"""Piper TTS — offline text-to-speech for treatment instructions.

Uses piper-tts when available, falls back gracefully when not installed.
Generated audio is stored in a session temp directory, cleaned up on close.

Feature flag: config.features.enable_tts
"""

from __future__ import annotations

import atexit
import contextlib
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from malaika.config import MalaikaConfig

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Language -> Piper voice model mapping
# ---------------------------------------------------------------------------

_VOICE_MODELS: dict[str, str] = {
    "en": "en_US-lessac-medium",
    "sw": "sw_CD-lanfrica-medium",
    "hi": "hi_IN-swara-medium",
    "fr": "fr_FR-siwis-medium",
}

_DEFAULT_LANGUAGE = "en"


class MalaikaTTS:
    """Offline text-to-speech using Piper TTS.

    Generates WAV files from text, with per-session temp storage.
    Falls back to a no-op when piper-tts is not installed.

    Usage:
        config = load_config()
        tts = MalaikaTTS(config)
        wav_path = tts.speak("Give oral rehydration salts", language="en")
        if wav_path:
            # play wav_path
            ...
        tts.cleanup()
    """

    def __init__(self, config: MalaikaConfig) -> None:
        self._config = config
        self._piper_available = False
        self._piper_module: Any = None
        self._temp_dir: Path | None = None
        self._file_counter: int = 0

        if not config.features.enable_tts:
            logger.info("tts_disabled", reason="enable_tts=False")
            return

        # Try importing piper
        try:
            import piper  # type: ignore[import-untyped]

            self._piper_module = piper
            self._piper_available = True
            logger.info("tts_initialized", backend="piper-tts")
        except ImportError:
            logger.warning(
                "tts_piper_unavailable",
                msg="piper-tts not installed. TTS will be disabled. "
                "Install with: pip install piper-tts",
            )

        # Create temp directory for generated audio
        if self._piper_available:
            self._temp_dir = Path(tempfile.mkdtemp(prefix="malaika_tts_"))
            atexit.register(self._cleanup_atexit)
            logger.info("tts_temp_dir_created", path=str(self._temp_dir))

    @property
    def available(self) -> bool:
        """Whether TTS is available and enabled."""
        return self._piper_available and self._config.features.enable_tts

    @property
    def supported_languages(self) -> list[str]:
        """List of supported language codes."""
        return list(_VOICE_MODELS.keys())

    def speak(self, text: str, language: str = "en") -> Path | None:
        """Generate speech audio from text.

        Args:
            text: Text to speak.
            language: Language code (en, sw, hi, fr).

        Returns:
            Path to generated WAV file, or None if TTS is unavailable.
        """
        if not self.available:
            logger.debug("tts_speak_skipped", reason="TTS unavailable or disabled")
            return None

        if not text.strip():
            logger.debug("tts_speak_skipped", reason="Empty text")
            return None

        voice = _VOICE_MODELS.get(language, _VOICE_MODELS[_DEFAULT_LANGUAGE])

        if self._temp_dir is None:
            logger.error("tts_no_temp_dir")
            return None

        self._file_counter += 1
        output_path = self._temp_dir / f"tts_{self._file_counter:04d}_{language}.wav"

        try:
            return self._generate_audio(text, voice, output_path)
        except Exception as exc:
            logger.error(
                "tts_generation_failed",
                error=str(exc),
                language=language,
                text_length=len(text),
            )
            return None

    def _generate_audio(
        self,
        text: str,
        voice: str,
        output_path: Path,
    ) -> Path | None:
        """Generate audio using Piper TTS.

        Args:
            text: Text to synthesize.
            voice: Piper voice model name.
            output_path: Where to write the WAV file.

        Returns:
            Path to generated file, or None on failure.
        """
        if self._piper_module is None:
            return None

        try:
            import wave

            piper = self._piper_module
            voice_obj = piper.PiperVoice.load(voice)

            with wave.open(str(output_path), "wb") as wav_file:
                voice_obj.synthesize(text, wav_file)

            if output_path.exists() and output_path.stat().st_size > 0:
                logger.info(
                    "tts_generated",
                    path=str(output_path),
                    size_bytes=output_path.stat().st_size,
                    voice=voice,
                )
                return output_path

            logger.warning("tts_empty_output", path=str(output_path))
            return None

        except Exception as exc:
            logger.error("tts_piper_error", error=str(exc), voice=voice)
            return None

    def cleanup(self) -> None:
        """Remove all generated audio files and temp directory."""
        if self._temp_dir is not None and self._temp_dir.exists():
            try:
                shutil.rmtree(self._temp_dir)
                logger.info("tts_temp_dir_cleaned", path=str(self._temp_dir))
            except OSError as exc:
                logger.warning(
                    "tts_cleanup_failed",
                    error=str(exc),
                    path=str(self._temp_dir),
                )
            finally:
                self._temp_dir = None

    def _cleanup_atexit(self) -> None:
        """Atexit hook for cleanup — silent on errors."""
        with contextlib.suppress(Exception):
            self.cleanup()
