import pytest
from conftest import FakeChat

from docpilot.llm.providers import LLMConfigError, LLMRegistry


def test_falls_back_to_a_configured_provider_when_the_default_has_no_key() -> None:
    registry = LLMRegistry({"gemini": FakeChat()}, default_provider="anthropic")

    assert registry.default() == ("gemini", "gemini-3.8-flash")
    assert registry.resolve(None, None).provider == "gemini"


def test_configured_default_model_is_used_when_allowlisted() -> None:
    registry = LLMRegistry(
        {"anthropic": FakeChat()}, default_provider="anthropic", default_model="claude-haiku-5-5"
    )

    assert registry.resolve(None, None).model == "claude-haiku-5-5"


def test_no_configured_providers_is_a_clear_error() -> None:
    registry = LLMRegistry({}, default_provider="anthropic")

    assert registry.default() is None
    with pytest.raises(LLMConfigError, match="No LLM provider"):
        registry.resolve(None, None)


def test_unknown_provider_is_rejected() -> None:
    registry = LLMRegistry({"anthropic": FakeChat()}, default_provider="anthropic")

    with pytest.raises(LLMConfigError, match="Unknown provider"):
        registry.resolve("openai", None)
