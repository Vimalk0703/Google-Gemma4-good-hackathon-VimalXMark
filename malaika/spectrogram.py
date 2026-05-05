"""Spectrogram utility — convert audio files to mel-spectrogram images.

Gemma 4 cannot process audio natively via Transformers. This module converts
audio recordings to mel-spectrogram PNG images that Gemma 4 vision CAN analyze.

Pipeline: audio file → librosa mel-spectrogram → PIL image → temp PNG path

This is the preferred approach for breath sound classification because:
1. Spectrograms preserve acoustic features (frequency, intensity, timing)
2. Gemma 4 vision works reliably (confirmed in Session 1 Kaggle tests)
3. Fine-tuning on spectrogram images is straightforward via Unsloth

Dependencies: librosa, numpy, PIL (Pillow)
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()

# Spectrogram generation parameters — tuned for pediatric breath sounds
# Breath sounds: 100-2000 Hz range, so we use a lower fmax than music
DEFAULT_SR = 22050  # Sample rate (Hz) — librosa default
DEFAULT_N_FFT = 2048  # FFT window size
DEFAULT_HOP_LENGTH = 512  # Hop between frames
DEFAULT_N_MELS = 128  # Number of mel bands
DEFAULT_FMIN = 50  # Min frequency (Hz) — captures low grunting
DEFAULT_FMAX = 4000  # Max frequency (Hz) — captures high wheeze/stridor
DEFAULT_IMAGE_WIDTH = 512  # Output image width (pixels)
DEFAULT_IMAGE_HEIGHT = 256  # Output image height (pixels)


def audio_to_spectrogram(
    audio_path: Path,
    output_path: Path | None = None,
    *,
    sr: int = DEFAULT_SR,
    n_fft: int = DEFAULT_N_FFT,
    hop_length: int = DEFAULT_HOP_LENGTH,
    n_mels: int = DEFAULT_N_MELS,
    fmin: float = DEFAULT_FMIN,
    fmax: float = DEFAULT_FMAX,
    image_width: int = DEFAULT_IMAGE_WIDTH,
    image_height: int = DEFAULT_IMAGE_HEIGHT,
    duration: float | None = None,
) -> Path:
    """Convert an audio file to a mel-spectrogram PNG image.

    Args:
        audio_path: Path to audio file (WAV/MP3/OGG/FLAC).
        output_path: Where to save the PNG. If None, uses a temp file.
        sr: Target sample rate in Hz.
        n_fft: FFT window size.
        hop_length: Hop length between frames.
        n_mels: Number of mel frequency bands.
        fmin: Minimum frequency in Hz.
        fmax: Maximum frequency in Hz.
        image_width: Output image width in pixels.
        image_height: Output image height in pixels.
        duration: Max duration in seconds to process (None = full file).

    Returns:
        Path to the generated PNG spectrogram image.

    Raises:
        FileNotFoundError: If audio_path doesn't exist.
        RuntimeError: If librosa or PIL is not installed.
        ValueError: If audio cannot be loaded or processed.
    """
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    try:
        import librosa
        import numpy as np
    except ImportError as e:
        raise RuntimeError(
            "librosa and numpy are required for spectrogram generation. "
            "Install with: pip install librosa numpy"
        ) from e

    try:
        from PIL import Image
    except ImportError as e:
        raise RuntimeError(
            "Pillow is required for spectrogram image generation. Install with: pip install Pillow"
        ) from e

    logger.debug("generating_spectrogram", audio_path=str(audio_path))

    # Load audio
    try:
        y, loaded_sr = librosa.load(
            str(audio_path),
            sr=sr,
            duration=duration,
            mono=True,
        )
    except Exception as e:
        raise ValueError(f"Failed to load audio file: {e}") from e

    if len(y) == 0:
        raise ValueError(f"Audio file is empty: {audio_path}")

    # Compute mel spectrogram
    mel_spec: Any = librosa.feature.melspectrogram(
        y=y,
        sr=loaded_sr,
        n_fft=n_fft,
        hop_length=hop_length,
        n_mels=n_mels,
        fmin=fmin,
        fmax=fmax,
    )

    # Convert to dB scale (log scale for better visualization)
    mel_spec_db: Any = librosa.power_to_db(mel_spec, ref=np.max)

    # Normalize to 0-255 range for image
    spec_min = float(np.min(mel_spec_db))
    spec_max = float(np.max(mel_spec_db))
    if spec_max - spec_min > 0:
        normalized = ((mel_spec_db - spec_min) / (spec_max - spec_min) * 255).astype(np.uint8)
    else:
        normalized = np.zeros_like(mel_spec_db, dtype=np.uint8)

    # Flip vertically (low frequencies at bottom)
    normalized = np.flip(normalized, axis=0)

    # Create PIL image and resize
    img = Image.fromarray(normalized, mode="L")
    img = img.resize((image_width, image_height), Image.Resampling.LANCZOS)

    # Convert to RGB (Gemma 4 expects color images)
    img_rgb = img.convert("RGB")

    # Save
    if output_path is None:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        output_path = Path(tmp.name)
        tmp.close()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img_rgb.save(str(output_path))

    logger.debug(
        "spectrogram_generated",
        audio_path=str(audio_path),
        output_path=str(output_path),
        audio_duration=f"{len(y) / loaded_sr:.1f}s",
        image_size=f"{image_width}x{image_height}",
    )

    return output_path


def batch_audio_to_spectrograms(
    audio_dir: Path,
    output_dir: Path,
    *,
    pattern: str = "*.wav",
    **kwargs: Any,
) -> list[tuple[Path, Path]]:
    """Convert a directory of audio files to spectrogram images.

    Args:
        audio_dir: Directory containing audio files.
        output_dir: Directory to save spectrogram PNGs.
        pattern: Glob pattern for audio files.
        **kwargs: Additional arguments passed to audio_to_spectrogram.

    Returns:
        List of (audio_path, spectrogram_path) tuples.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[tuple[Path, Path]] = []

    audio_files = sorted(audio_dir.glob(pattern))
    logger.info("batch_spectrogram_start", count=len(audio_files))

    for audio_path in audio_files:
        spec_path = output_dir / f"{audio_path.stem}_spectrogram.png"
        try:
            audio_to_spectrogram(audio_path, spec_path, **kwargs)
            results.append((audio_path, spec_path))
        except (ValueError, FileNotFoundError) as e:
            logger.warning(
                "batch_spectrogram_skip",
                audio_path=str(audio_path),
                error=str(e),
            )

    logger.info("batch_spectrogram_done", converted=len(results), total=len(audio_files))
    return results
