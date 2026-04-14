"""Tests for Malaika TTS — offline text-to-speech.

All tests mock piper-tts since it may not be installed in the test environment.
Tests cover: initialization, speak with/without piper, cleanup, feature flag.
"""

from __future__ import annotations

import sys
import wave
from types import ModuleType
from unittest.mock import patch

import pytest

from malaika.config import MalaikaConfig, load_config


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tts_config() -> MalaikaConfig:
    """Config with TTS enabled."""
    return load_config()


@pytest.fixture
def tts_config_disabled() -> MalaikaConfig:
    """Config with TTS disabled."""
    cfg = load_config()
    cfg.features.enable_tts = False
    return cfg


@pytest.fixture
def mock_piper_module() -> ModuleType:
    """Create a mock piper module with PiperVoice."""
    mock_mod = ModuleType("piper")

    class MockPiperVoice:
        @staticmethod
        def load(voice_name: str) -> "MockPiperVoice":
            return MockPiperVoice()

        def synthesize(self, text: str, wav_file: wave.Wave_write) -> None:
            """Write a minimal valid WAV to the file."""
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(22050)
            wav_file.writeframes(b"\x00\x00" * 1000)

    mock_mod.PiperVoice = MockPiperVoice  # type: ignore[attr-defined]
    return mock_mod


# ---------------------------------------------------------------------------
# Initialization Tests
# ---------------------------------------------------------------------------

class TestTTSInitialization:
    """Tests for MalaikaTTS initialization."""

    def test_init_with_tts_disabled(self, tts_config_disabled: MalaikaConfig) -> None:
        """TTS disabled via feature flag should not attempt piper import."""
        from malaika.tts import MalaikaTTS

        tts = MalaikaTTS(tts_config_disabled)
        assert not tts.available

    def test_init_piper_not_installed(self, tts_config: MalaikaConfig) -> None:
        """When piper is not installed, TTS should gracefully fall back."""
        with patch.dict(sys.modules, {"piper": None}):
            from malaika.tts import MalaikaTTS

            tts = MalaikaTTS(tts_config)
            assert not tts.available

    def test_init_piper_available(
        self, tts_config: MalaikaConfig, mock_piper_module: ModuleType,
    ) -> None:
        """When piper is available, TTS should initialize successfully."""
        with patch.dict(sys.modules, {"piper": mock_piper_module}):
            from malaika.tts import MalaikaTTS

            tts = MalaikaTTS(tts_config)
            assert tts.available
            assert tts._temp_dir is not None
            assert tts._temp_dir.exists()
            tts.cleanup()

    def test_supported_languages(self, tts_config: MalaikaConfig) -> None:
        """Check supported language list."""
        from malaika.tts import MalaikaTTS

        tts = MalaikaTTS(tts_config)
        langs = tts.supported_languages
        assert "en" in langs


# ---------------------------------------------------------------------------
# Speak Tests
# ---------------------------------------------------------------------------

class TestTTSSpeak:
    """Tests for the speak() method."""

    def test_speak_when_unavailable_returns_none(
        self, tts_config: MalaikaConfig,
    ) -> None:
        """speak() returns None when piper is not available."""
        with patch.dict(sys.modules, {"piper": None}):
            from malaika.tts import MalaikaTTS

            tts = MalaikaTTS(tts_config)
            result = tts.speak("Hello world")
            assert result is None

    def test_speak_empty_text_returns_none(
        self, tts_config: MalaikaConfig, mock_piper_module: ModuleType,
    ) -> None:
        """speak() with empty text returns None."""
        with patch.dict(sys.modules, {"piper": mock_piper_module}):
            from malaika.tts import MalaikaTTS

            tts = MalaikaTTS(tts_config)
            result = tts.speak("")
            assert result is None
            result2 = tts.speak("   ")
            assert result2 is None
            tts.cleanup()

    def test_speak_generates_wav(
        self, tts_config: MalaikaConfig, mock_piper_module: ModuleType,
    ) -> None:
        """speak() generates a valid WAV file path."""
        with patch.dict(sys.modules, {"piper": mock_piper_module}):
            from malaika.tts import MalaikaTTS

            tts = MalaikaTTS(tts_config)
            result = tts.speak("Give oral rehydration salts")

            assert result is not None
            assert result.exists()
            assert result.suffix == ".wav"
            assert result.stat().st_size > 0
            tts.cleanup()

    def test_speak_increments_file_counter(
        self, tts_config: MalaikaConfig, mock_piper_module: ModuleType,
    ) -> None:
        """Each call to speak() creates a new file with incrementing counter."""
        with patch.dict(sys.modules, {"piper": mock_piper_module}):
            from malaika.tts import MalaikaTTS

            tts = MalaikaTTS(tts_config)
            r1 = tts.speak("First message")
            r2 = tts.speak("Second message")

            assert r1 is not None
            assert r2 is not None
            assert r1 != r2
            assert "0001" in r1.name
            assert "0002" in r2.name
            tts.cleanup()

    def test_speak_with_different_languages(
        self, tts_config: MalaikaConfig, mock_piper_module: ModuleType,
    ) -> None:
        """speak() uses correct language code in filename."""
        with patch.dict(sys.modules, {"piper": mock_piper_module}):
            from malaika.tts import MalaikaTTS

            tts = MalaikaTTS(tts_config)
            r_en = tts.speak("Hello", language="en")
            r_sw = tts.speak("Jambo", language="sw")

            assert r_en is not None
            assert r_sw is not None
            assert "_en.wav" in r_en.name
            assert "_sw.wav" in r_sw.name
            tts.cleanup()

    def test_speak_unknown_language_falls_back_to_english(
        self, tts_config: MalaikaConfig, mock_piper_module: ModuleType,
    ) -> None:
        """Unknown language code falls back to English voice."""
        with patch.dict(sys.modules, {"piper": mock_piper_module}):
            from malaika.tts import MalaikaTTS

            tts = MalaikaTTS(tts_config)
            result = tts.speak("Test", language="zz")
            assert result is not None
            tts.cleanup()

    def test_speak_handles_piper_exception(
        self, tts_config: MalaikaConfig,
    ) -> None:
        """speak() handles exceptions from piper gracefully."""
        mock_mod = ModuleType("piper")

        class FailingVoice:
            @staticmethod
            def load(voice_name: str) -> "FailingVoice":
                return FailingVoice()

            def synthesize(self, text: str, wav_file: wave.Wave_write) -> None:
                raise RuntimeError("Piper synthesis failed")

        mock_mod.PiperVoice = FailingVoice  # type: ignore[attr-defined]

        with patch.dict(sys.modules, {"piper": mock_mod}):
            from malaika.tts import MalaikaTTS

            tts = MalaikaTTS(tts_config)
            result = tts.speak("This should fail gracefully")
            assert result is None
            tts.cleanup()

    def test_speak_disabled_via_feature_flag(
        self, tts_config_disabled: MalaikaConfig,
    ) -> None:
        """speak() returns None when TTS feature is disabled."""
        from malaika.tts import MalaikaTTS

        tts = MalaikaTTS(tts_config_disabled)
        result = tts.speak("Hello")
        assert result is None


# ---------------------------------------------------------------------------
# Cleanup Tests
# ---------------------------------------------------------------------------

class TestTTSCleanup:
    """Tests for cleanup behavior."""

    def test_cleanup_removes_temp_dir(
        self, tts_config: MalaikaConfig, mock_piper_module: ModuleType,
    ) -> None:
        """cleanup() removes the temp directory and all contents."""
        with patch.dict(sys.modules, {"piper": mock_piper_module}):
            from malaika.tts import MalaikaTTS

            tts = MalaikaTTS(tts_config)
            temp_dir = tts._temp_dir
            assert temp_dir is not None

            tts.speak("Generate a file")
            assert any(temp_dir.iterdir())

            tts.cleanup()
            assert not temp_dir.exists()
            assert tts._temp_dir is None

    def test_cleanup_idempotent(
        self, tts_config: MalaikaConfig, mock_piper_module: ModuleType,
    ) -> None:
        """Calling cleanup() twice does not raise."""
        with patch.dict(sys.modules, {"piper": mock_piper_module}):
            from malaika.tts import MalaikaTTS

            tts = MalaikaTTS(tts_config)
            tts.cleanup()
            tts.cleanup()  # Should not raise

    def test_cleanup_when_no_temp_dir(self, tts_config: MalaikaConfig) -> None:
        """Cleanup when no temp dir was created (piper not available)."""
        with patch.dict(sys.modules, {"piper": None}):
            from malaika.tts import MalaikaTTS

            tts = MalaikaTTS(tts_config)
            tts.cleanup()  # Should not raise
