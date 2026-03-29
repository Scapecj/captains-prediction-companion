"""Shared defaults for LLM steps that use the OpenRouter API."""

from __future__ import annotations

import os

DEFAULT_OPENROUTER_MODEL = "openrouter/free"


def resolve_openrouter_model(
    env_var: str, fallback: str = DEFAULT_OPENROUTER_MODEL
) -> str:
    """Return a configured OpenRouter model or a safe free-model fallback."""
    value = os.getenv(env_var)
    if value is None:
        return fallback
    cleaned = value.strip()
    return cleaned or fallback


def get_pipeline_model_defaults() -> dict[str, str]:
    """Return the effective default models for the pipeline."""
    return {
        "implications": resolve_openrouter_model("IMPLICATIONS_MODEL"),
        "validation": resolve_openrouter_model("VALIDATION_MODEL"),
    }
