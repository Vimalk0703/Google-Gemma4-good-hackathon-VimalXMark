"""Tests for prompt templates — rendering, validation, and registry.

These tests verify that prompts render correctly, enforce required variables,
and handle multimodal content properly. They do NOT test model output quality.
"""

from __future__ import annotations

import pytest

from malaika.prompts import PromptRegistry
from malaika.prompts.base import PromptTemplate


# Import domain modules to trigger registration
from malaika.prompts import (  # noqa: F401
    breathing,
    danger_signs,
    diarrhea,
    fever,
    heart,
    nutrition,
    speech,
    treatment,
)


class TestPromptRegistry:
    """Tests for the PromptRegistry singleton."""

    @pytest.fixture(autouse=True)
    def _isolate_registry(self, clean_registry: None) -> None:  # type: ignore[misc]
        """Clear registry for all tests in this class."""

    def test_register_and_get(self) -> None:
        prompt = PromptTemplate(
            name="test.example",
            version="1.0.0",
            description="Test prompt",
            system_prompt="You are a test.",
            user_template="Say hello.",
        )
        PromptRegistry.register(prompt)
        retrieved = PromptRegistry.get("test.example")
        assert retrieved.name == "test.example"

    def test_duplicate_name_raises(self) -> None:
        prompt = PromptTemplate(
            name="test.dup",
            version="1.0.0",
            description="First",
            system_prompt="",
            user_template="",
        )
        PromptRegistry.register(prompt)
        with pytest.raises(ValueError, match="Duplicate prompt name"):
            PromptRegistry.register(prompt)

    def test_get_missing_raises(self) -> None:
        with pytest.raises(KeyError, match="Prompt not found"):
            PromptRegistry.get("nonexistent.prompt")

    def test_list_all_sorted(self) -> None:
        PromptRegistry.register(PromptTemplate(
            name="test.zzz", version="1.0.0", description="", system_prompt="", user_template="",
        ))
        PromptRegistry.register(PromptTemplate(
            name="test.aaa", version="1.0.0", description="", system_prompt="", user_template="",
        ))
        names = PromptRegistry.list_all()
        assert names == sorted(names)

    def test_clear(self) -> None:
        PromptRegistry.register(PromptTemplate(
            name="test.clear", version="1.0.0", description="", system_prompt="", user_template="",
        ))
        assert "test.clear" in PromptRegistry.list_all()
        PromptRegistry.clear()
        assert PromptRegistry.list_all() == []


class TestPromptTemplate:
    """Tests for PromptTemplate rendering."""

    def test_render_text_only(self) -> None:
        prompt = PromptTemplate(
            name="test.render",
            version="1.0.0",
            description="Test",
            system_prompt="You are helpful.",
            user_template="Count to {number}.",
            required_variables=frozenset({"number"}),
        )
        messages = prompt.render(number=5)
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "You are helpful." in messages[0]["content"]
        assert messages[1]["role"] == "user"
        assert "Count to 5." in messages[1]["content"]

    def test_render_includes_injection_defense(self) -> None:
        prompt = PromptTemplate(
            name="test.defense",
            version="1.0.0",
            description="Test",
            system_prompt="System.",
            user_template="Hello.",
        )
        messages = prompt.render()
        assert "Respond ONLY" in messages[0]["content"]

    def test_render_missing_variable_raises(self) -> None:
        prompt = PromptTemplate(
            name="test.missing",
            version="1.0.0",
            description="Test",
            system_prompt="",
            user_template="Hello {name}.",
            required_variables=frozenset({"name"}),
        )
        with pytest.raises(ValueError, match="Missing required variables"):
            prompt.render()

    def test_render_multimodal_image(self) -> None:
        prompt = PromptTemplate(
            name="test.multimodal",
            version="1.0.0",
            description="Test",
            system_prompt="Analyze.",
            user_template="What do you see?",
        )
        messages = prompt.render_multimodal(media={"image": "/path/to/img.jpg"})
        user_msg = messages[-1]
        assert user_msg["role"] == "user"
        assert isinstance(user_msg["content"], list)
        assert user_msg["content"][0]["type"] == "image"
        assert user_msg["content"][0]["image"] == "/path/to/img.jpg"
        assert user_msg["content"][-1]["type"] == "text"

    def test_render_multimodal_audio(self) -> None:
        prompt = PromptTemplate(
            name="test.audio",
            version="1.0.0",
            description="Test",
            system_prompt="Listen.",
            user_template="What do you hear?",
        )
        messages = prompt.render_multimodal(media={"audio": "/path/to/clip.wav"})
        assert messages[-1]["content"][0]["type"] == "audio"

    def test_render_multimodal_invalid_type_raises(self) -> None:
        prompt = PromptTemplate(
            name="test.invalid_media",
            version="1.0.0",
            description="Test",
            system_prompt="",
            user_template="Hello.",
        )
        with pytest.raises(ValueError, match="Invalid media type"):
            prompt.render_multimodal(media={"pdf": "/path/to/doc.pdf"})

    def test_render_no_system_prompt(self) -> None:
        prompt = PromptTemplate(
            name="test.no_system",
            version="1.0.0",
            description="Test",
            system_prompt="",
            user_template="Just user message.",
        )
        messages = prompt.render()
        assert len(messages) == 1
        assert messages[0]["role"] == "user"


class TestDomainPromptRendering:
    """Verify all registered domain prompts render without errors."""

    @pytest.fixture(autouse=True)
    def _ensure_prompts_registered(self) -> None:  # type: ignore[misc]
        """Re-register all domain prompts (may have been cleared by earlier tests)."""
        if not PromptRegistry.list_all():
            import importlib
            PromptRegistry.clear()
            from malaika.prompts import (
                breathing as _b, danger_signs as _d, diarrhea as _di,
                fever as _f, heart as _h, nutrition as _n, speech as _sp, treatment as _t,
            )
            for mod in [_b, _d, _di, _f, _h, _n, _sp, _t]:
                importlib.reload(mod)

    def test_breathing_count_rate_renders(self) -> None:
        prompt = PromptRegistry.get("breathing.count_rate_from_video")
        messages = prompt.render_multimodal(
            media={"video": "/test/chest.mp4"},
            duration_seconds=15,
        )
        assert "15-second" in messages[-1]["content"][-1]["text"]

    def test_breathing_indrawing_renders(self) -> None:
        prompt = PromptRegistry.get("breathing.detect_chest_indrawing")
        messages = prompt.render_multimodal(media={"image": "/test/chest.jpg"})
        assert len(messages) >= 1

    def test_breathing_sounds_renders(self) -> None:
        prompt = PromptRegistry.get("breathing.classify_breath_sounds")
        messages = prompt.render_multimodal(media={"audio": "/test/breath.wav"})
        assert len(messages) >= 1

    def test_danger_alertness_renders(self) -> None:
        prompt = PromptRegistry.get("danger.assess_alertness")
        messages = prompt.render_multimodal(media={"image": "/test/child.jpg"})
        assert len(messages) >= 1

    def test_treatment_renders_with_variables(self) -> None:
        prompt = PromptRegistry.get("treatment.generate_plan")
        messages = prompt.render(
            classifications="Pneumonia",
            urgency="YELLOW",
            language="Swahili",
            child_age_months=6,
        )
        assert "Pneumonia" in messages[-1]["content"]
        assert prompt.temperature == 0.3
        assert prompt.expected_output_format == "text"

    def test_speech_renders(self) -> None:
        prompt = PromptRegistry.get("speech.understand_response")
        messages = prompt.render_multimodal(
            media={"audio": "/test/speech.wav"},
            question_asked="Does the child have diarrhea?",
        )
        assert "diarrhea" in messages[-1]["content"][-1]["text"]

    def test_all_prompts_have_version(self) -> None:
        """Every registered prompt must have a version."""
        for name in PromptRegistry.list_all():
            prompt = PromptRegistry.get(name)
            assert prompt.version, f"Prompt {name} has no version"
            parts = prompt.version.split(".")
            assert len(parts) == 3, f"Prompt {name} version not semver: {prompt.version}"

    def test_all_clinical_prompts_temp_zero(self) -> None:
        """All clinical prompts must use temperature 0.0 (except treatment)."""
        for name in PromptRegistry.list_all():
            prompt = PromptRegistry.get(name)
            if "treatment" not in name:
                assert prompt.temperature == 0.0, (
                    f"Prompt {name} has temperature {prompt.temperature}, "
                    f"expected 0.0 for clinical prompts"
                )
