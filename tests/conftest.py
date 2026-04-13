"""Shared test fixtures for Malaika tests."""

from __future__ import annotations

import importlib

import pytest

from malaika.config import GuardConfig, MalaikaConfig, load_config
from malaika.prompts import PromptRegistry


@pytest.fixture
def config() -> MalaikaConfig:
    """Default Malaika configuration for tests."""
    return load_config()


@pytest.fixture
def guard_config() -> GuardConfig:
    """Guard configuration for tests."""
    return GuardConfig()


@pytest.fixture
def clean_registry() -> None:  # type: ignore[misc]
    """Clear prompt registry before a test. Use explicitly, not autouse."""
    PromptRegistry.clear()


@pytest.fixture(autouse=True)
def _auto_restore_prompt_registry() -> None:  # type: ignore[misc]
    """Ensure all domain prompts are registered before each test.

    Handles the case where a prior test cleared the registry.
    Clears first to avoid duplicate registration errors, then reloads.
    """
    if not PromptRegistry.list_all():
        PromptRegistry.clear()
        from malaika.prompts import (
            breathing,
            danger_signs,
            diarrhea,
            fever,
            heart,
            nutrition,
            speech,
            treatment,
        )
        for mod in [breathing, danger_signs, diarrhea, fever, heart, nutrition, speech, treatment]:
            importlib.reload(mod)
