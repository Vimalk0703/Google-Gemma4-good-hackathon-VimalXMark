"""Input Guard — Layer 1: Validate files before they reach the model.

Checks: file exists, is regular file, correct format (by magic bytes),
within size limits, no path traversal.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from malaika.types import ValidatedInput

if TYPE_CHECKING:
    from pathlib import Path

    from malaika.config import GuardConfig


class InputValidationError(Exception):
    """File failed input validation. Do not process this file."""


# ---------------------------------------------------------------------------
# Magic byte signatures for format detection
# ---------------------------------------------------------------------------

_MAGIC_SIGNATURES: dict[str, list[tuple[bytes, int]]] = {
    # Images
    "JPEG": [(b"\xff\xd8\xff", 0)],
    "PNG": [(b"\x89PNG\r\n\x1a\n", 0)],
    "WEBP": [(b"RIFF", 0), (b"WEBP", 8)],  # Must match both
    # Audio
    "WAV": [(b"RIFF", 0), (b"WAVE", 8)],
    "MP3": [(b"\xff\xfb", 0)],  # MPEG frame sync
    "MP3_ID3": [(b"ID3", 0)],  # ID3 tagged MP3
    "OGG": [(b"OggS", 0)],
    "FLAC": [(b"fLaC", 0)],
    # Video
    "MP4": [(b"ftyp", 4)],  # Offset 4 after size bytes
    "WEBM": [(b"\x1a\x45\xdf\xa3", 0)],  # EBML header
    "AVI": [(b"RIFF", 0), (b"AVI ", 8)],
}

# Map detected format to canonical name
_FORMAT_ALIASES: dict[str, str] = {
    "MP3_ID3": "MP3",
}

# Map media type to allowed formats
_ALLOWED_FORMATS: dict[str, frozenset[str]] = {
    "image": frozenset({"JPEG", "PNG", "WEBP"}),
    "audio": frozenset({"WAV", "MP3", "OGG", "FLAC"}),
    "video": frozenset({"MP4", "WEBM", "AVI"}),
}

# Map media type to config field name for size limit
_SIZE_LIMIT_FIELDS: dict[str, str] = {
    "image": "max_image_size_mb",
    "audio": "max_audio_size_mb",
    "video": "max_video_size_mb",
}


def identify_format(file_path: Path) -> str | None:
    """Identify file format by reading magic bytes. Never trust extensions.

    Args:
        file_path: Path to the file.

    Returns:
        Canonical format string (e.g., "JPEG", "WAV") or None if unknown.
    """
    try:
        with file_path.open("rb") as f:
            header = f.read(32)  # Read enough for all signatures
    except OSError:
        return None

    if len(header) < 4:
        return None

    for fmt, signatures in _MAGIC_SIGNATURES.items():
        match = True
        for magic_bytes, offset in signatures:
            if offset + len(magic_bytes) > len(header):
                match = False
                break
            if header[offset : offset + len(magic_bytes)] != magic_bytes:
                match = False
                break
        if match:
            return _FORMAT_ALIASES.get(fmt, fmt)

    return None


def validate_file(
    file_path: Path,
    media_type: str,
    config: GuardConfig,
) -> ValidatedInput:
    """Validate a file for processing. Full input guard pipeline.

    Args:
        file_path: Path to the file to validate.
        media_type: One of "image", "audio", "video".
        config: Guard configuration.

    Returns:
        ValidatedInput with confirmed format and size.

    Raises:
        InputValidationError: With specific reason if any check fails.
    """
    # 0. Valid media type
    if media_type not in _ALLOWED_FORMATS:
        raise InputValidationError(
            f"Invalid media type: '{media_type}'. Must be one of: {set(_ALLOWED_FORMATS.keys())}"
        )

    # 1. File exists and is a regular file (not symlink, not directory)
    if not file_path.exists():
        raise InputValidationError(f"File does not exist: {file_path.name}")

    if not file_path.is_file():
        raise InputValidationError(
            f"Not a regular file (may be directory or symlink): {file_path.name}"
        )

    # 2. No path traversal
    try:
        resolved = file_path.resolve()
    except OSError as e:
        raise InputValidationError(f"Cannot resolve file path: {e}") from e

    if ".." in file_path.parts:
        raise InputValidationError("Path traversal detected: '..' in path")

    # 3. File size within limits
    size_bytes = resolved.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    max_size_mb = getattr(config, _SIZE_LIMIT_FIELDS[media_type])

    if size_mb > max_size_mb:
        raise InputValidationError(
            f"File too large: {size_mb:.1f}MB (limit: {max_size_mb}MB for {media_type})"
        )

    if size_bytes == 0:
        raise InputValidationError("File is empty (0 bytes)")

    # 4. Format detection by magic bytes
    detected_format = identify_format(resolved)
    if detected_format is None:
        raise InputValidationError(
            f"Unknown file format. Could not identify by magic bytes. "
            f"Allowed {media_type} formats: {_ALLOWED_FORMATS[media_type]}"
        )

    # 5. Format allowed for this media type
    allowed = _ALLOWED_FORMATS[media_type]
    if detected_format not in allowed:
        raise InputValidationError(
            f"Format '{detected_format}' is not allowed for {media_type}. Allowed: {allowed}"
        )

    return ValidatedInput(
        file_path=resolved,
        media_type=media_type,
        format_detected=detected_format,
        size_bytes=size_bytes,
    )
