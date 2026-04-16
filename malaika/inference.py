"""MalaikaInference — single Gemma 4 model interface for all modalities.

Loads Gemma 4 once via Transformers + BitsAndBytes 4-bit quantization.
Provides typed methods for text, image, audio, and video inference.
Includes self-correction retry and response cache.

This module MUST NOT contain any clinical logic or thresholds.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import structlog

from malaika.config import MalaikaConfig
from malaika.guards.output_validator import OutputParseError, build_correction_prompt
from malaika.observability.cost_tracker import CostTracker
from malaika.prompts.base import PromptTemplate
from malaika.types import ValidatedOutput

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ModelError(Exception):
    """Gemma 4 inference failed (OOM, load failure, generation error)."""


# ---------------------------------------------------------------------------
# Response Cache
# ---------------------------------------------------------------------------

class _ResponseCache:
    """Hash-based dict cache for inference responses.

    Keyed on (prompt_name, prompt_version, input_hash, temperature).
    Invalidated on model reload. Disabled for treatment prompts.
    """

    def __init__(self, max_entries: int = 100) -> None:
        self._cache: dict[str, str] = {}
        self._max_entries = max_entries

    def _make_key(
        self,
        prompt_name: str,
        prompt_version: str,
        input_hash: str,
        temperature: float,
    ) -> str:
        raw = f"{prompt_name}|{prompt_version}|{input_hash}|{temperature}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(
        self,
        prompt_name: str,
        prompt_version: str,
        input_hash: str,
        temperature: float,
    ) -> str | None:
        key = self._make_key(prompt_name, prompt_version, input_hash, temperature)
        return self._cache.get(key)

    def put(
        self,
        prompt_name: str,
        prompt_version: str,
        input_hash: str,
        temperature: float,
        response: str,
    ) -> None:
        if len(self._cache) >= self._max_entries:
            # Evict oldest (first inserted)
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        key = self._make_key(prompt_name, prompt_version, input_hash, temperature)
        self._cache[key] = response

    def clear(self) -> None:
        self._cache.clear()

    @property
    def size(self) -> int:
        return len(self._cache)


# ---------------------------------------------------------------------------
# MalaikaInference
# ---------------------------------------------------------------------------

class MalaikaInference:
    """Single Gemma 4 model loaded once via Transformers + BitsAndBytes 4-bit.

    Provides typed methods for each modality and integrates self-correction
    retry, response caching, and cost tracking.

    Usage:
        config = load_config()
        inference = MalaikaInference(config)
        inference.load_model()
        result = inference.generate(messages, max_tokens=150, temperature=0.0)
    """

    def __init__(self, config: MalaikaConfig) -> None:
        self._config = config
        self._model: Any = None
        self._processor: Any = None
        self._device: str = "cpu"
        self._model_loaded: bool = False
        self._cache = _ResponseCache(max_entries=config.model.max_cache_entries)
        self.cost_tracker = CostTracker()

    @property
    def model_loaded(self) -> bool:
        """Whether the model is currently loaded."""
        return self._model_loaded

    @property
    def device(self) -> str:
        """Current device the model is on."""
        return self._device

    @property
    def cache(self) -> _ResponseCache:
        """Access the response cache (for testing/inspection)."""
        return self._cache

    def load_model(self) -> None:
        """Load Gemma 4 model with 4-bit quantization.

        Raises:
            ModelError: If model loading fails (no GPU, OOM, etc.).
        """
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoProcessor

            # Determine device
            if torch.cuda.is_available():
                self._device = "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self._device = "mps"
            else:
                self._device = "cpu"

            model_name = self._config.model.model_name

            logger.info(
                "loading_model",
                model_name=model_name,
                device=self._device,
                quantize_4bit=self._config.model.quantize_4bit,
            )

            load_kwargs: dict[str, Any] = {
                "device_map": "auto" if self._device != "cpu" else None,
            }

            if self._config.model.quantize_4bit and self._device == "cuda":
                try:
                    from transformers import BitsAndBytesConfig

                    load_kwargs["quantization_config"] = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch.float16,
                    )
                except ImportError:
                    logger.warning("bitsandbytes_unavailable", msg="Falling back to full precision")

            # Try merged model first, fall back to base model
            try:
                self._processor = AutoProcessor.from_pretrained(
                    model_name, trust_remote_code=True,
                )
                self._model = AutoModelForCausalLM.from_pretrained(
                    model_name, trust_remote_code=True, **load_kwargs,
                )
                logger.info("model_loaded_merged", model_name=model_name)
            except Exception as e:
                if model_name != self._config.model.base_model_name:
                    logger.warning(
                        "merged_model_unavailable",
                        error=str(e),
                        fallback=self._config.model.base_model_name,
                    )
                    model_name = self._config.model.base_model_name
                    self._processor = AutoProcessor.from_pretrained(
                        model_name, trust_remote_code=True,
                    )
                    self._model = AutoModelForCausalLM.from_pretrained(
                        model_name, trust_remote_code=True, **load_kwargs,
                    )
                else:
                    raise

            # Load LoRA adapter only if NOT using merged model (merged has LoRA baked in)
            if model_name == self._config.model.base_model_name:
                adapter_path = self._config.model.breath_sounds_adapter
                if (
                    self._config.model.enable_breath_sounds_adapter
                    and adapter_path.exists()
                    and (adapter_path / "adapter_config.json").exists()
                ):
                    try:
                        from peft import PeftModel

                        self._model = PeftModel.from_pretrained(self._model, str(adapter_path))
                        logger.info("lora_adapter_loaded", adapter_path=str(adapter_path))
                    except ImportError:
                        logger.warning("peft_not_installed", msg="LoRA adapter skipped — install peft")
                    except Exception as e:
                        logger.warning("lora_adapter_failed", error=str(e))
            else:
                logger.info("lora_skip_merged_model", msg="Using merged model — LoRA already baked in")

            self._model_loaded = True
            self._cache.clear()

            logger.info("model_loaded", device=self._device)

        except ImportError as e:
            raise ModelError(
                f"Required packages not available: {e}. "
                f"Install torch, transformers, and optionally bitsandbytes."
            ) from e
        except Exception as e:
            raise ModelError(f"Failed to load model: {e}") from e

    def unload_model(self) -> None:
        """Unload model and free memory."""
        self._model = None
        self._processor = None
        self._model_loaded = False
        self._cache.clear()

        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

        logger.info("model_unloaded")

    def _extract_images_from_messages(
        self, messages: list[dict[str, Any]],
    ) -> list[Any]:
        """Extract image paths from multimodal messages and load as PIL Images."""
        images: list[Any] = []
        try:
            from PIL import Image
        except ImportError:
            return images

        for msg in messages:
            content = msg.get("content")
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "image":
                        image_path = part.get("image", "")
                        if image_path and Path(image_path).exists():
                            images.append(Image.open(image_path).convert("RGB"))
        return images

    def generate(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        """Core generation method. Sends messages to Gemma 4 and returns raw text.

        Handles text-only and multimodal (image) inputs. Images referenced
        in messages are loaded from disk and passed through the processor.

        Args:
            messages: Chat messages in Gemma 4 format.
            max_tokens: Maximum tokens to generate (defaults to config).
            temperature: Sampling temperature (defaults to config).

        Returns:
            Raw text response from Gemma 4.

        Raises:
            ModelError: If model is not loaded or generation fails.
        """
        if not self._model_loaded:
            raise ModelError("Model not loaded. Call load_model() first.")

        max_tokens = max_tokens or self._config.model.default_max_tokens
        temperature = temperature if temperature is not None else self._config.model.default_temperature

        with self.cost_tracker.track_call() as cost:
            try:
                import torch

                with torch.inference_mode():
                    # Extract images from multimodal messages
                    images = self._extract_images_from_messages(messages)

                    # Build prompt text from chat template
                    prompt_text = self._processor.apply_chat_template(
                        messages,
                        add_generation_prompt=True,
                        tokenize=False,
                    )

                    # Tokenize with processor — pass images if present
                    processor_kwargs: dict[str, Any] = {
                        "text": prompt_text,
                        "return_tensors": "pt",
                    }
                    if images:
                        processor_kwargs["images"] = images

                    inputs = self._processor(**processor_kwargs)

                    # Move to model device
                    inputs = {
                        k: v.to(self._model.device) if hasattr(v, "to") else v
                        for k, v in inputs.items()
                    }

                    gen_kwargs: dict[str, Any] = {
                        "max_new_tokens": max_tokens,
                    }
                    if temperature > 0:
                        gen_kwargs["temperature"] = temperature
                        gen_kwargs["do_sample"] = True
                    else:
                        gen_kwargs["do_sample"] = False

                    outputs = self._model.generate(**inputs, **gen_kwargs)
                    input_len = inputs["input_ids"].shape[-1]

                    generated_tokens = outputs[0][input_len:]
                    response = self._processor.decode(
                        generated_tokens, skip_special_tokens=True,
                    )

                    cost.tokens_in = input_len
                    cost.tokens_out = len(generated_tokens)

                    return response.strip()

            except ImportError as e:
                raise ModelError(f"Required packages not available: {e}") from e
            except Exception as e:
                raise ModelError(f"Generation failed: {e}") from e

    def generate_with_retry(
        self,
        messages: list[dict[str, Any]],
        prompt: PromptTemplate,
        input_hash: str = "",
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> tuple[str, ValidatedOutput, int]:
        """Generate with self-correction retry on parse failure.

        If output_validator rejects output, retries with correction prompt
        up to config.model.max_retries times.

        Args:
            messages: Chat messages.
            prompt: The PromptTemplate used (for schema validation).
            input_hash: Hash of input data for caching.
            max_tokens: Maximum tokens.
            temperature: Sampling temperature.

        Returns:
            Tuple of (raw_output, validated_output, retries_used).

        Raises:
            ModelError: If generation itself fails.
        """
        from malaika.guards.output_validator import validate_output

        max_tokens = max_tokens or prompt.max_tokens
        temperature = temperature if temperature is not None else prompt.temperature
        max_retries = self._config.model.max_retries if self._config.features.enable_self_correction else 0

        # Check cache (disabled for treatment prompts)
        is_treatment = "treatment" in prompt.name
        if self._config.features.enable_response_cache and not is_treatment:
            cached = self._cache.get(prompt.name, prompt.version, input_hash, temperature)
            if cached is not None:
                logger.debug("cache_hit", prompt_name=prompt.name)
                try:
                    validated = validate_output(cached, prompt, self._config.guards)
                    return cached, validated, 0
                except OutputParseError:
                    # Cached response no longer valid (schema changed?), proceed
                    pass

        raw_output = ""
        last_error = ""
        retries_used = 0
        conversation = list(messages)

        for attempt in range(1 + max_retries):
            raw_output = self.generate(conversation, max_tokens=max_tokens, temperature=temperature)

            try:
                validated = validate_output(raw_output, prompt, self._config.guards)

                # Cache successful response (not treatment)
                if self._config.features.enable_response_cache and not is_treatment:
                    self._cache.put(prompt.name, prompt.version, input_hash, temperature, raw_output)

                return raw_output, validated, retries_used

            except OutputParseError as e:
                last_error = str(e)
                retries_used = attempt + 1

                if attempt < max_retries:
                    correction = build_correction_prompt(
                        original_prompt=prompt,
                        failed_output=raw_output,
                        error_message=last_error,
                        attempt=attempt + 1,
                    )
                    # Append model's failed response and correction to conversation
                    conversation.append({"role": "assistant", "content": raw_output})
                    conversation.append({"role": "user", "content": correction})

                    logger.warning(
                        "self_correction_retry",
                        prompt_name=prompt.name,
                        attempt=attempt + 1,
                        error=last_error[:200],
                    )

        # All retries exhausted — return uncertain
        logger.error(
            "self_correction_exhausted",
            prompt_name=prompt.name,
            retries=retries_used,
            last_error=last_error[:200],
        )

        return raw_output, ValidatedOutput(
            status="uncertain",
            parsed={},
            raw_output=raw_output,
            retries_used=retries_used,
        ), retries_used

    # -------------------------------------------------------------------
    # Convenience methods for each modality
    # -------------------------------------------------------------------

    def analyze_image(
        self,
        image_path: Path | str,
        prompt: PromptTemplate,
        input_hash: str = "",
        **variables: Any,
    ) -> tuple[str, ValidatedOutput, int]:
        """Analyze an image using a prompt template.

        Args:
            image_path: Path to the image file.
            prompt: PromptTemplate for the analysis.
            input_hash: Hash of input for caching.
            **variables: Template variables.

        Returns:
            Tuple of (raw_output, validated_output, retries_used).
        """
        messages = prompt.render_multimodal(
            media={"image": str(image_path)},
            **variables,
        )
        return self.generate_with_retry(
            messages, prompt, input_hash=input_hash,
            max_tokens=prompt.max_tokens, temperature=prompt.temperature,
        )

    def analyze_audio(
        self,
        audio_path: Path | str,
        prompt: PromptTemplate,
        input_hash: str = "",
        **variables: Any,
    ) -> tuple[str, ValidatedOutput, int]:
        """Analyze audio using a prompt template.

        Args:
            audio_path: Path to the audio file.
            prompt: PromptTemplate for the analysis.
            input_hash: Hash of input for caching.
            **variables: Template variables.

        Returns:
            Tuple of (raw_output, validated_output, retries_used).
        """
        messages = prompt.render_multimodal(
            media={"audio": str(audio_path)},
            **variables,
        )
        return self.generate_with_retry(
            messages, prompt, input_hash=input_hash,
            max_tokens=prompt.max_tokens, temperature=prompt.temperature,
        )

    def analyze_video(
        self,
        video_path: Path | str,
        prompt: PromptTemplate,
        input_hash: str = "",
        **variables: Any,
    ) -> tuple[str, ValidatedOutput, int]:
        """Analyze video using a prompt template.

        Args:
            video_path: Path to the video file.
            prompt: PromptTemplate for the analysis.
            input_hash: Hash of input for caching.
            **variables: Template variables.

        Returns:
            Tuple of (raw_output, validated_output, retries_used).
        """
        messages = prompt.render_multimodal(
            media={"video": str(video_path)},
            **variables,
        )
        return self.generate_with_retry(
            messages, prompt, input_hash=input_hash,
            max_tokens=prompt.max_tokens, temperature=prompt.temperature,
        )

    def reason(
        self,
        prompt: PromptTemplate,
        input_hash: str = "",
        **variables: Any,
    ) -> tuple[str, ValidatedOutput, int]:
        """Text-only reasoning using a prompt template.

        Args:
            prompt: PromptTemplate for the reasoning task.
            input_hash: Hash of input for caching.
            **variables: Template variables.

        Returns:
            Tuple of (raw_output, validated_output, retries_used).
        """
        messages = prompt.render(**variables)
        return self.generate_with_retry(
            messages, prompt, input_hash=input_hash,
            max_tokens=prompt.max_tokens, temperature=prompt.temperature,
        )
