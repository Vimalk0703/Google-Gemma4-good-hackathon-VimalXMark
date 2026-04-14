"""Tests for spectrogram utility — audio to mel-spectrogram image conversion.

Tests cover error cases and the batch function. The core conversion
is tested with real librosa/PIL on Kaggle (notebook 04).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from malaika.spectrogram import audio_to_spectrogram, batch_audio_to_spectrograms


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_audio(tmp_path: Path) -> Path:
    """Create a minimal WAV file for testing."""
    wav = tmp_path / "test.wav"
    wav.write_bytes(b"RIFF" + b"\x00" * 4 + b"WAVE" + b"\x00" * 100)
    return wav


# ---------------------------------------------------------------------------
# audio_to_spectrogram Tests
# ---------------------------------------------------------------------------

class TestAudioToSpectrogram:
    """Tests for audio_to_spectrogram function."""

    def test_file_not_found(self) -> None:
        """Should raise FileNotFoundError for missing audio."""
        with pytest.raises(FileNotFoundError):
            audio_to_spectrogram(Path("/nonexistent/audio.wav"))

    def test_librosa_not_installed(self, temp_audio: Path) -> None:
        """Should raise RuntimeError if librosa is not available."""
        with patch.dict(sys.modules, {"librosa": None}):
            with pytest.raises(RuntimeError, match="librosa"):
                audio_to_spectrogram(temp_audio)

    def test_pil_not_installed(self, temp_audio: Path) -> None:
        """Should raise RuntimeError if PIL is not available."""
        mock_librosa = MagicMock()
        import numpy as np
        mock_librosa.load.return_value = (np.random.randn(22050).astype(np.float32), 22050)
        mock_librosa.feature.melspectrogram.return_value = np.random.rand(128, 44).astype(np.float32)
        mock_librosa.power_to_db.return_value = np.random.uniform(-80, 0, (128, 44)).astype(np.float32)

        with patch.dict(sys.modules, {
            "librosa": mock_librosa,
            "librosa.feature": mock_librosa.feature,
            "PIL": None,
            "PIL.Image": None,
        }):
            with pytest.raises(RuntimeError, match="Pillow"):
                audio_to_spectrogram(temp_audio)

    def test_load_failure_raises_valueerror(self, temp_audio: Path) -> None:
        """Should raise ValueError if audio cannot be loaded."""
        mock_librosa = MagicMock()
        mock_librosa.load.side_effect = Exception("Unsupported format")
        mock_pil = MagicMock()

        with patch.dict(sys.modules, {
            "librosa": mock_librosa,
            "librosa.feature": mock_librosa.feature,
            "PIL": mock_pil,
            "PIL.Image": mock_pil.Image,
        }):
            with pytest.raises(ValueError, match="Failed to load"):
                audio_to_spectrogram(temp_audio)

    def test_empty_audio_raises_valueerror(self, temp_audio: Path) -> None:
        """Should raise ValueError for empty audio."""
        import numpy as np
        mock_librosa = MagicMock()
        mock_librosa.load.return_value = (np.array([], dtype=np.float32), 22050)
        mock_pil = MagicMock()

        with patch.dict(sys.modules, {
            "librosa": mock_librosa,
            "librosa.feature": mock_librosa.feature,
            "PIL": mock_pil,
            "PIL.Image": mock_pil.Image,
        }):
            with pytest.raises(ValueError, match="empty"):
                audio_to_spectrogram(temp_audio)

    def test_default_parameters(self) -> None:
        """Verify default parameter values are reasonable for breath sounds."""
        from malaika.spectrogram import (
            DEFAULT_FMAX,
            DEFAULT_FMIN,
            DEFAULT_IMAGE_HEIGHT,
            DEFAULT_IMAGE_WIDTH,
            DEFAULT_N_MELS,
            DEFAULT_SR,
        )
        assert DEFAULT_SR == 22050
        assert DEFAULT_FMIN == 50       # Low enough for grunting
        assert DEFAULT_FMAX == 4000     # High enough for stridor
        assert DEFAULT_N_MELS == 128
        assert DEFAULT_IMAGE_WIDTH == 512
        assert DEFAULT_IMAGE_HEIGHT == 256


# ---------------------------------------------------------------------------
# batch_audio_to_spectrograms Tests
# ---------------------------------------------------------------------------

class TestBatchAudioToSpectrograms:
    """Tests for batch_audio_to_spectrograms function."""

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Should return empty list for directory with no matching files."""
        input_dir = tmp_path / "audio"
        input_dir.mkdir()
        output_dir = tmp_path / "specs"

        result = batch_audio_to_spectrograms(input_dir, output_dir)
        assert result == []
        assert output_dir.exists()

    def test_creates_output_directory(self, tmp_path: Path) -> None:
        """Should create the output directory if it doesn't exist."""
        input_dir = tmp_path / "audio"
        input_dir.mkdir()
        output_dir = tmp_path / "nested" / "specs"

        batch_audio_to_spectrograms(input_dir, output_dir)
        assert output_dir.exists()

    def test_custom_pattern(self, tmp_path: Path) -> None:
        """Should respect custom glob pattern."""
        input_dir = tmp_path / "audio"
        input_dir.mkdir()
        # Create .mp3 files but search for .wav
        (input_dir / "test.mp3").write_bytes(b"fake mp3")
        output_dir = tmp_path / "specs"

        result = batch_audio_to_spectrograms(input_dir, output_dir, pattern="*.wav")
        assert result == []  # No .wav files found
