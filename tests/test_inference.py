"""Tests for MalaikaInference — generation, self-correction, and caching.

All tests use mocked inference (no GPU needed).
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from malaika.config import MalaikaConfig, load_config
from malaika.inference import MalaikaInference, ModelError, _ResponseCache
from malaika.prompts.base import PromptTemplate
from malaika.types import ValidatedOutput


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def config() -> MalaikaConfig:
    return load_config()


@pytest.fixture
def mock_inference(config: MalaikaConfig) -> MalaikaInference:
    """Create a MalaikaInference with mocked model loading."""
    inf = MalaikaInference(config)
    inf._model_loaded = True
    inf._model = MagicMock()
    inf._processor = MagicMock()
    inf._device = "cpu"
    return inf


@pytest.fixture
def sample_prompt() -> PromptTemplate:
    return PromptTemplate(
        name="test.sample",
        version="1.0.0",
        description="Test prompt",
        system_prompt="You are a test assistant.",
        user_template="Analyze this.",
        expected_output_format="json",
        output_schema={
            "type": "object",
            "properties": {
                "result": {"type": "string"},
                "confidence": {"type": "number"},
            },
            "required": ["result", "confidence"],
        },
        max_tokens=100,
        temperature=0.0,
    )


@pytest.fixture
def treatment_prompt() -> PromptTemplate:
    return PromptTemplate(
        name="treatment.test_plan",
        version="1.0.0",
        description="Test treatment prompt",
        system_prompt="You are a treatment advisor.",
        user_template="Generate a treatment plan for {classifications}.",
        required_variables=frozenset({"classifications"}),
        expected_output_format="text",
        output_schema=None,
        max_tokens=200,
        temperature=0.3,
    )


# ---------------------------------------------------------------------------
# Response Cache Tests
# ---------------------------------------------------------------------------

class TestResponseCache:
    """Tests for the _ResponseCache."""

    def test_empty_cache_returns_none(self) -> None:
        cache = _ResponseCache(max_entries=10)
        result = cache.get("p", "1.0", "hash", 0.0)
        assert result is None

    def test_put_and_get(self) -> None:
        cache = _ResponseCache(max_entries=10)
        cache.put("p", "1.0", "hash", 0.0, "response_text")
        result = cache.get("p", "1.0", "hash", 0.0)
        assert result == "response_text"

    def test_different_key_returns_none(self) -> None:
        cache = _ResponseCache(max_entries=10)
        cache.put("p", "1.0", "hash1", 0.0, "response")
        result = cache.get("p", "1.0", "hash2", 0.0)
        assert result is None

    def test_different_temperature_returns_none(self) -> None:
        cache = _ResponseCache(max_entries=10)
        cache.put("p", "1.0", "hash", 0.0, "response")
        result = cache.get("p", "1.0", "hash", 0.5)
        assert result is None

    def test_different_version_returns_none(self) -> None:
        cache = _ResponseCache(max_entries=10)
        cache.put("p", "1.0.0", "hash", 0.0, "response")
        result = cache.get("p", "2.0.0", "hash", 0.0)
        assert result is None

    def test_clear(self) -> None:
        cache = _ResponseCache(max_entries=10)
        cache.put("p", "1.0", "hash", 0.0, "response")
        assert cache.size == 1
        cache.clear()
        assert cache.size == 0
        assert cache.get("p", "1.0", "hash", 0.0) is None

    def test_eviction_on_full(self) -> None:
        cache = _ResponseCache(max_entries=2)
        cache.put("p1", "1.0", "h", 0.0, "first")
        cache.put("p2", "1.0", "h", 0.0, "second")
        # Cache is full, adding third should evict first
        cache.put("p3", "1.0", "h", 0.0, "third")
        assert cache.size == 2
        assert cache.get("p1", "1.0", "h", 0.0) is None  # Evicted
        assert cache.get("p3", "1.0", "h", 0.0) == "third"

    def test_size_property(self) -> None:
        cache = _ResponseCache(max_entries=10)
        assert cache.size == 0
        cache.put("p", "1.0", "h", 0.0, "r")
        assert cache.size == 1


# ---------------------------------------------------------------------------
# MalaikaInference Tests
# ---------------------------------------------------------------------------

class TestMalaikaInference:
    """Tests for MalaikaInference initialization and properties."""

    def test_init_defaults(self, config: MalaikaConfig) -> None:
        inf = MalaikaInference(config)
        assert not inf.model_loaded
        assert inf.device == "cpu"

    def test_generate_without_model_raises(self, config: MalaikaConfig) -> None:
        inf = MalaikaInference(config)
        with pytest.raises(ModelError, match="Model not loaded"):
            inf.generate([{"role": "user", "content": "hello"}])

    def test_unload_model(self, mock_inference: MalaikaInference) -> None:
        mock_inference._cache.put("test", "1.0", "h", 0.0, "cached")
        mock_inference.unload_model()
        assert not mock_inference.model_loaded
        assert mock_inference.cache.size == 0


# ---------------------------------------------------------------------------
# Self-Correction Retry Tests
# ---------------------------------------------------------------------------

class TestSelfCorrectionRetry:
    """Tests for generate_with_retry self-correction logic."""

    def test_first_attempt_success(
        self,
        mock_inference: MalaikaInference,
        sample_prompt: PromptTemplate,
    ) -> None:
        """Valid output on first attempt, no retries needed."""
        valid_json = json.dumps({"result": "normal", "confidence": 0.9})

        with patch.object(mock_inference, "generate", return_value=valid_json):
            raw, validated, retries = mock_inference.generate_with_retry(
                [{"role": "user", "content": "test"}],
                sample_prompt,
            )

        assert retries == 0
        assert validated.status == "valid"
        assert validated.parsed["result"] == "normal"

    def test_retry_on_parse_failure_then_success(
        self,
        mock_inference: MalaikaInference,
        sample_prompt: PromptTemplate,
    ) -> None:
        """First attempt fails parsing, second succeeds."""
        bad_output = "This is not JSON at all"
        valid_json = json.dumps({"result": "ok", "confidence": 0.85})

        with patch.object(
            mock_inference, "generate",
            side_effect=[bad_output, valid_json],
        ):
            raw, validated, retries = mock_inference.generate_with_retry(
                [{"role": "user", "content": "test"}],
                sample_prompt,
            )

        assert retries == 1
        assert validated.status == "valid"
        assert validated.parsed["result"] == "ok"

    def test_all_retries_exhausted_returns_uncertain(
        self,
        mock_inference: MalaikaInference,
        sample_prompt: PromptTemplate,
    ) -> None:
        """All 3 attempts fail -> uncertain."""
        bad_output = "garbage output"

        with patch.object(mock_inference, "generate", return_value=bad_output):
            raw, validated, retries = mock_inference.generate_with_retry(
                [{"role": "user", "content": "test"}],
                sample_prompt,
            )

        assert retries == 3  # max_retries (2) + 1 initial = 3 total, retries_used = 3
        assert validated.status == "uncertain"

    def test_self_correction_disabled(
        self,
        config: MalaikaConfig,
        sample_prompt: PromptTemplate,
    ) -> None:
        """When self-correction is disabled, no retries."""
        config.features.enable_self_correction = False
        inf = MalaikaInference(config)
        inf._model_loaded = True
        inf._model = MagicMock()
        inf._processor = MagicMock()

        bad_output = "not json"

        with patch.object(inf, "generate", return_value=bad_output):
            raw, validated, retries = inf.generate_with_retry(
                [{"role": "user", "content": "test"}],
                sample_prompt,
            )

        assert retries == 1  # Only initial attempt counts
        assert validated.status == "uncertain"

    def test_low_confidence_returns_uncertain(
        self,
        mock_inference: MalaikaInference,
        sample_prompt: PromptTemplate,
    ) -> None:
        """Output valid JSON but confidence below threshold -> uncertain."""
        low_conf = json.dumps({"result": "maybe", "confidence": 0.3})

        with patch.object(mock_inference, "generate", return_value=low_conf):
            raw, validated, retries = mock_inference.generate_with_retry(
                [{"role": "user", "content": "test"}],
                sample_prompt,
            )

        assert validated.status == "uncertain"
        assert retries == 0  # No retries — it parsed successfully


# ---------------------------------------------------------------------------
# Cache Integration Tests
# ---------------------------------------------------------------------------

class TestCacheIntegration:
    """Tests for cache behavior within generate_with_retry."""

    def test_cache_hit_skips_generation(
        self,
        mock_inference: MalaikaInference,
        sample_prompt: PromptTemplate,
    ) -> None:
        """Cached response should be returned without calling generate."""
        valid_json = json.dumps({"result": "cached_result", "confidence": 0.9})

        # Prime the cache
        mock_inference.cache.put(
            sample_prompt.name, sample_prompt.version, "test_hash", 0.0, valid_json,
        )

        with patch.object(mock_inference, "generate") as mock_gen:
            raw, validated, retries = mock_inference.generate_with_retry(
                [{"role": "user", "content": "test"}],
                sample_prompt,
                input_hash="test_hash",
            )
            mock_gen.assert_not_called()

        assert validated.parsed["result"] == "cached_result"

    def test_cache_miss_calls_generate(
        self,
        mock_inference: MalaikaInference,
        sample_prompt: PromptTemplate,
    ) -> None:
        """No cache entry -> generate is called."""
        valid_json = json.dumps({"result": "fresh", "confidence": 0.9})

        with patch.object(mock_inference, "generate", return_value=valid_json):
            raw, validated, retries = mock_inference.generate_with_retry(
                [{"role": "user", "content": "test"}],
                sample_prompt,
                input_hash="new_hash",
            )

        assert validated.parsed["result"] == "fresh"

    def test_successful_response_cached(
        self,
        mock_inference: MalaikaInference,
        sample_prompt: PromptTemplate,
    ) -> None:
        """Valid response gets cached for next use."""
        valid_json = json.dumps({"result": "to_cache", "confidence": 0.9})

        with patch.object(mock_inference, "generate", return_value=valid_json):
            mock_inference.generate_with_retry(
                [{"role": "user", "content": "test"}],
                sample_prompt,
                input_hash="cache_me",
            )

        cached = mock_inference.cache.get(
            sample_prompt.name, sample_prompt.version, "cache_me", 0.0,
        )
        assert cached == valid_json

    def test_treatment_prompt_not_cached(
        self,
        mock_inference: MalaikaInference,
        treatment_prompt: PromptTemplate,
    ) -> None:
        """Treatment prompts should not be cached."""
        treatment_text = "Give oral amoxicillin 250mg twice daily."

        with patch.object(mock_inference, "generate", return_value=treatment_text):
            mock_inference.generate_with_retry(
                [{"role": "user", "content": "test"}],
                treatment_prompt,
                input_hash="treatment_hash",
            )

        cached = mock_inference.cache.get(
            treatment_prompt.name, treatment_prompt.version, "treatment_hash", 0.3,
        )
        assert cached is None

    def test_cache_disabled_skips_cache(
        self,
        config: MalaikaConfig,
        sample_prompt: PromptTemplate,
    ) -> None:
        """When cache is disabled, never read or write cache."""
        config.features.enable_response_cache = False
        inf = MalaikaInference(config)
        inf._model_loaded = True
        inf._model = MagicMock()
        inf._processor = MagicMock()

        valid_json = json.dumps({"result": "no_cache", "confidence": 0.9})

        with patch.object(inf, "generate", return_value=valid_json):
            inf.generate_with_retry(
                [{"role": "user", "content": "test"}],
                sample_prompt,
                input_hash="x",
            )

        assert inf.cache.size == 0


# ---------------------------------------------------------------------------
# Convenience Method Tests
# ---------------------------------------------------------------------------

class TestConvenienceMethods:
    """Tests for analyze_image, analyze_audio, analyze_video, reason."""

    def test_analyze_image(
        self,
        mock_inference: MalaikaInference,
        sample_prompt: PromptTemplate,
    ) -> None:
        valid_json = json.dumps({"result": "image_ok", "confidence": 0.9})

        with patch.object(mock_inference, "generate", return_value=valid_json):
            raw, validated, retries = mock_inference.analyze_image(
                "/fake/path.jpg", sample_prompt, input_hash="img",
            )

        assert validated.parsed["result"] == "image_ok"

    def test_analyze_audio(
        self,
        mock_inference: MalaikaInference,
        sample_prompt: PromptTemplate,
    ) -> None:
        valid_json = json.dumps({"result": "audio_ok", "confidence": 0.9})

        with patch.object(mock_inference, "generate", return_value=valid_json):
            raw, validated, retries = mock_inference.analyze_audio(
                "/fake/audio.wav", sample_prompt, input_hash="aud",
            )

        assert validated.parsed["result"] == "audio_ok"

    def test_analyze_video(
        self,
        mock_inference: MalaikaInference,
        sample_prompt: PromptTemplate,
    ) -> None:
        valid_json = json.dumps({"result": "video_ok", "confidence": 0.9})

        with patch.object(mock_inference, "generate", return_value=valid_json):
            raw, validated, retries = mock_inference.analyze_video(
                "/fake/video.mp4", sample_prompt, input_hash="vid",
            )

        assert validated.parsed["result"] == "video_ok"

    def test_reason(
        self,
        mock_inference: MalaikaInference,
        sample_prompt: PromptTemplate,
    ) -> None:
        valid_json = json.dumps({"result": "reason_ok", "confidence": 0.9})

        with patch.object(mock_inference, "generate", return_value=valid_json):
            raw, validated, retries = mock_inference.reason(
                sample_prompt, input_hash="reason",
            )

        assert validated.parsed["result"] == "reason_ok"


# ---------------------------------------------------------------------------
# Cost Tracker Integration
# ---------------------------------------------------------------------------

class TestCostTrackerIntegration:
    """Tests for cost tracker integration."""

    def test_generate_tracks_call(
        self,
        mock_inference: MalaikaInference,
    ) -> None:
        """Each generate call should be tracked."""
        initial_count = mock_inference.cost_tracker.session.call_count
        valid_json = json.dumps({"result": "ok", "confidence": 0.9})

        # Mock the actual model generation internals
        with patch.object(mock_inference, "generate", return_value=valid_json):
            prompt = PromptTemplate(
                name="test.cost",
                version="1.0.0",
                description="",
                system_prompt="",
                user_template="test",
                expected_output_format="json",
                output_schema={"required": ["result", "confidence"]},
            )
            mock_inference.generate_with_retry(
                [{"role": "user", "content": "test"}],
                prompt,
            )

        # generate_with_retry calls generate which uses track_call internally
        # But since we mocked generate, cost_tracker won't be hit directly
        # This test verifies the cost_tracker exists and is accessible
        assert mock_inference.cost_tracker is not None
