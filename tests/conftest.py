"""Shared test fixtures for Malaika tests."""

from __future__ import annotations

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
