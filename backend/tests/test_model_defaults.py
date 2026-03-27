from core.model_defaults import (
    DEFAULT_OPENROUTER_MODEL,
    get_pipeline_model_defaults,
    resolve_openrouter_model,
)


def test_openrouter_model_defaults_to_free_router(monkeypatch):
    monkeypatch.delenv("IMPLICATIONS_MODEL", raising=False)
    monkeypatch.delenv("VALIDATION_MODEL", raising=False)

    assert resolve_openrouter_model("IMPLICATIONS_MODEL") == DEFAULT_OPENROUTER_MODEL
    assert resolve_openrouter_model("VALIDATION_MODEL") == DEFAULT_OPENROUTER_MODEL
    assert get_pipeline_model_defaults() == {
        "implications": DEFAULT_OPENROUTER_MODEL,
        "validation": DEFAULT_OPENROUTER_MODEL,
    }


def test_openrouter_model_defaults_allow_overrides(monkeypatch):
    monkeypatch.setenv("IMPLICATIONS_MODEL", "google/gemini-2.5-flash")
    monkeypatch.setenv("VALIDATION_MODEL", "google/gemini-3-flash-preview")

    assert resolve_openrouter_model("IMPLICATIONS_MODEL") == "google/gemini-2.5-flash"
    assert resolve_openrouter_model("VALIDATION_MODEL") == "google/gemini-3-flash-preview"
    assert get_pipeline_model_defaults() == {
        "implications": "google/gemini-2.5-flash",
        "validation": "google/gemini-3-flash-preview",
    }
