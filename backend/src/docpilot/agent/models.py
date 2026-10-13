from collections.abc import Callable
from functools import lru_cache
from typing import TYPE_CHECKING

from docpilot.config import Settings, get_settings

if TYPE_CHECKING:  # LangChain loads on the first agent run, keeping cold starts quick
    from langchain_core.language_models import BaseChatModel

# Builds a LangChain chat model for an allowlisted (provider, model) at a token limit.
ModelFactory = Callable[[str, str, int], "BaseChatModel"]


def make_model_factory(settings: Settings) -> ModelFactory:
    def build(provider: str, model: str, max_tokens: int) -> "BaseChatModel":
        if provider == "anthropic":
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(
                model=model,
                api_key=settings.anthropic_api_key.get_secret_value(),
                max_tokens=max_tokens,
                max_retries=2,
            )
        if provider == "openai":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=model,
                api_key=settings.openai_api_key.get_secret_value(),
                max_tokens=max_tokens,
                max_retries=2,
                use_responses_api=True,
                store=False,  # don't keep document passages on OpenAI's side
                stream_usage=True,
            )
        if provider == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=model,
                api_key=settings.gemini_api_key.get_secret_value(),
                max_tokens=max_tokens,
                max_retries=3,  # the free tier allows only a few requests a minute
            )
        raise ValueError(f"No agent model for provider '{provider}'")

    return build


@lru_cache
def get_model_factory() -> ModelFactory:
    """FastAPI dependency, overridden in tests with scripted models."""
    return make_model_factory(get_settings())
