"""Malaika configuration — single source of truth for all settings.

Feature flags, model paths, thresholds, and parameters.
Load from configs/features.yaml if present, otherwise use defaults.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent
ADAPTERS_DIR = PROJECT_ROOT / "adapters"
DATA_DIR = PROJECT_ROOT / "data"
CONFIGS_DIR = PROJECT_ROOT / "configs"


# ---------------------------------------------------------------------------
# Feature Flags
# ---------------------------------------------------------------------------

@dataclass
class FeatureFlags:
    """Feature flags — toggle modules without code changes."""

    enable_heart_rate: bool = False      # MEMS heart module (GO/NO-GO pending)
    enable_tts: bool = True              # Piper TTS spoken output
    enable_video_breathing: bool = True  # Breathing rate from video (vs frame fallback)
    enable_multilingual: bool = True     # Multi-language support
    enable_response_cache: bool = True   # Hash-based inference cache
    enable_self_correction: bool = True  # Retry with correction prompt on parse failure


# ---------------------------------------------------------------------------
# Model Configuration
# ---------------------------------------------------------------------------

@dataclass
class ModelConfig:
    """Gemma 4 model configuration."""

    # Model identity — use merged fine-tuned model if available, else base
    model_name: str = "Vimal0703/malaika-breath-sounds-E4B-merged"
    base_model_name: str = "google/gemma-4-E4B-it"
    quantize_4bit: bool = True

    # Whisper model for audio transcription (Gemma 4 does NOT support audio input)
    whisper_model_name: str = "openai/whisper-small"

    # Inference defaults
    default_max_tokens: int = 512
    default_temperature: float = 0.0  # Deterministic for clinical tasks
    treatment_temperature: float = 0.3  # Slightly creative for language generation

    # Self-correction
    max_retries: int = 2  # Max correction retries (3 total attempts)

    # Cache
    max_cache_entries: int = 100  # Per-session cache limit

    # LoRA adapter for breath sound classification (binary: normal vs abnormal)
    breath_sounds_adapter: Path = field(default_factory=lambda: ADAPTERS_DIR)
    enable_breath_sounds_adapter: bool = True


# ---------------------------------------------------------------------------
# Guard Configuration
# ---------------------------------------------------------------------------

@dataclass
class GuardConfig:
    """Security guard thresholds."""

    # Input guard — file size limits (MB)
    max_image_size_mb: int = 20
    max_audio_size_mb: int = 50
    max_video_size_mb: int = 200

    # Content filter
    max_text_input_length: int = 2000  # Characters

    # Output validator
    minimum_confidence: float = 0.6  # Below this -> Uncertain


# ---------------------------------------------------------------------------
# Audio / Video Configuration
# ---------------------------------------------------------------------------

@dataclass
class MediaConfig:
    """Audio and video recording/processing parameters."""

    # Breathing rate video
    breathing_video_duration_seconds: int = 15
    breathing_video_fps: int = 15

    # Audio recording
    audio_sample_rate: int = 16000  # 16kHz for speech
    audio_max_duration_seconds: int = 30

    # Supported formats (validated by magic bytes in input_guard)
    allowed_image_formats: frozenset[str] = field(
        default_factory=lambda: frozenset({"JPEG", "PNG", "WEBP"})
    )
    allowed_audio_formats: frozenset[str] = field(
        default_factory=lambda: frozenset({"WAV", "MP3", "OGG", "FLAC"})
    )
    allowed_video_formats: frozenset[str] = field(
        default_factory=lambda: frozenset({"MP4", "WEBM", "AVI"})
    )


# ---------------------------------------------------------------------------
# Observability Configuration
# ---------------------------------------------------------------------------

@dataclass
class ObservabilityConfig:
    """Tracing and cost tracking settings."""

    # Trace output
    max_raw_output_length: int = 500  # Truncate raw model output in traces
    trace_output_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "traces")

    # Cost tracking
    track_vram: bool = True


# ---------------------------------------------------------------------------
# Master Config
# ---------------------------------------------------------------------------

@dataclass
class MalaikaConfig:
    """Top-level configuration aggregating all sub-configs."""

    features: FeatureFlags = field(default_factory=FeatureFlags)
    model: ModelConfig = field(default_factory=ModelConfig)
    guards: GuardConfig = field(default_factory=GuardConfig)
    media: MediaConfig = field(default_factory=MediaConfig)
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)


def load_config() -> MalaikaConfig:
    """Load configuration. Returns defaults for now.

    TODO: Load overrides from configs/features.yaml when it exists.
    """
    return MalaikaConfig()
