"""Prompt Registry — central lookup for all versioned prompt templates.

Usage:
    from malaika.prompts import PromptRegistry

    prompt = PromptRegistry.get("breathing.count_rate_from_video")
    messages = prompt.render(duration_seconds=15)
"""

from __future__ import annotations

from malaika.prompts.base import PromptTemplate


class PromptRegistry:
    """Central registry for all Malaika prompts. Singleton pattern via class methods."""

    _prompts: dict[str, PromptTemplate] = {}

    @classmethod
    def register(cls, prompt: PromptTemplate) -> PromptTemplate:
        """Register a prompt template. Raises on duplicate name.

        Args:
            prompt: The PromptTemplate to register.

        Returns:
            The same prompt (for inline registration).

        Raises:
            ValueError: If a prompt with this name is already registered.
        """
        if prompt.name in cls._prompts:
            raise ValueError(
                f"Duplicate prompt name: '{prompt.name}'. "
                f"Each prompt must have a unique name."
            )
        cls._prompts[prompt.name] = prompt
        return prompt

    @classmethod
    def get(cls, name: str) -> PromptTemplate:
        """Get a registered prompt by name.

        Args:
            name: The prompt name (e.g., "breathing.count_rate_from_video").

        Returns:
            The registered PromptTemplate.

        Raises:
            KeyError: If no prompt with this name is registered.
        """
        if name not in cls._prompts:
            available = sorted(cls._prompts.keys())
            raise KeyError(
                f"Prompt not found: '{name}'. "
                f"Available prompts: {available}"
            )
        return cls._prompts[name]

    @classmethod
    def list_all(cls) -> list[str]:
        """List all registered prompt names, sorted alphabetically."""
        return sorted(cls._prompts.keys())

    @classmethod
    def clear(cls) -> None:
        """Clear all registered prompts. Only use in tests."""
        cls._prompts.clear()


__all__ = ["PromptRegistry", "PromptTemplate"]
