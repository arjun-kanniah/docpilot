from collections.abc import Collection, Mapping
from dataclasses import dataclass, replace
from functools import lru_cache

from docpilot.config import get_settings
from docpilot.llm.base import ChatModel


@dataclass(frozen=True)
class ProviderInfo:
    id: str
    label: str
    models: tuple[str, ...]  # the first one is the provider's default


# The allowlist: requests may only pick from these. Add a model here to offer it.
CATALOG: dict[str, ProviderInfo] = {
    "anthropic": ProviderInfo(
        "anthropic", "Claude", ("claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5")
    ),
    "gemini": ProviderInfo("gemini", "Gemini", ("gemini-3.8-flash", "gemini-3.5-flash-lite")),
    "openai": ProviderInfo("openai", "OpenAI", ("gpt-6.1-sol", "gpt-6-luna", "gpt-6-astra")),
}

_KEY_NAMES = {
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
}


class LLMConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Choice:
    provider: str
    model: str
    chat: ChatModel


class LLMRegistry:
    """Resolves a (provider, model) request against the allowlist and the configured keys.

    `allowed` narrows the catalog further, e.g. to cheap models on the public demo.
    """

    def __init__(
        self,
        clients: Mapping[str, ChatModel],
        default_provider: str,
        default_model: str | None = None,
        allowed: Collection[str] | None = None,
    ) -> None:
        self._clients = dict(clients)
        self._default_provider = default_provider
        self._default_model = default_model
        self._allowed = set(allowed) if allowed is not None else None

    def _models(self, provider: str) -> tuple[str, ...]:
        models = CATALOG[provider].models
        return tuple(m for m in models if self._allowed is None or m in self._allowed)

    def available(self) -> list[ProviderInfo]:
        return [
            replace(info, models=self._models(pid))
            for pid, info in CATALOG.items()
            if pid in self._clients and self._models(pid)
        ]

    def default(self) -> tuple[str, str] | None:
        """The configured default, or the first usable provider if it isn't available."""
        usable = [info.id for info in self.available()]
        if not usable:
            return None
        provider = self._default_provider if self._default_provider in usable else usable[0]
        models = self._models(provider)
        return provider, self._default_model if self._default_model in models else models[0]

    def resolve(self, provider: str | None, model: str | None) -> Choice:
        if provider is None:
            fallback = self.default()
            if fallback is None:
                raise LLMConfigError(
                    f"No LLM provider is configured. Set one of: {', '.join(_KEY_NAMES.values())}."
                )
            provider = fallback[0]
            model = model or fallback[1]

        info = CATALOG.get(provider)
        if info is None:
            raise LLMConfigError(
                f"Unknown provider '{provider}'. Choose from: {', '.join(CATALOG)}."
            )
        if provider not in self._clients:
            raise LLMConfigError(f"{info.label} isn't configured. Set {_KEY_NAMES[provider]}.")
        models = self._models(provider)
        if not models:
            raise LLMConfigError(f"{info.label} isn't offered here.")
        model = model or models[0]
        if model not in models:
            raise LLMConfigError(
                f"Model '{model}' isn't offered for {info.label}. Choose from: {', '.join(models)}."
            )
        return Choice(provider, model, self._clients[provider])


@lru_cache
def get_llm_registry() -> LLMRegistry:
    from docpilot.llm.claude import ClaudeChat  # SDK imports are deferred until first use
    from docpilot.llm.gemini import GeminiChat
    from docpilot.llm.openai_chat import OpenAIChat

    settings = get_settings()
    clients: dict[str, ChatModel] = {}
    if key := settings.anthropic_api_key.get_secret_value():
        clients["anthropic"] = ClaudeChat(key)
    if key := settings.gemini_api_key.get_secret_value():
        clients["gemini"] = GeminiChat(key)
    if key := settings.openai_api_key.get_secret_value():
        clients["openai"] = OpenAIChat(key)
    return LLMRegistry(
        clients, settings.llm_provider, settings.llm_model, allowed=settings.allowed_models
    )
