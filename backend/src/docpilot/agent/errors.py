def friendly_error(exc: Exception) -> str | None:
    """A message safe to show users for a provider failure, or None if it isn't one.

    LangChain wraps each provider's errors in shared types (ModelRateLimitError and so on),
    so one check covers Claude, OpenAI and Gemini; the SDKs' own types are a fallback.
    """
    import anthropic  # SDK imports are deferred until first use
    import openai
    from langchain_core import exceptions as lc

    if isinstance(exc, lc.ModelAuthenticationError | anthropic.AuthenticationError):
        return "The provider rejected the API key."
    if isinstance(exc, lc.ModelRateLimitError | anthropic.RateLimitError | openai.RateLimitError):
        return (
            "The provider's rate limit or quota was reached. "
            "Try again shortly or pick another model."
        )
    if isinstance(
        exc, lc.ModelConnectionError | lc.ModelTimeoutError | anthropic.APIConnectionError
    ):
        return "Could not reach the provider. Try again shortly."
    if isinstance(exc, lc.ModelError | anthropic.APIStatusError | openai.APIStatusError):
        return "The provider returned an error. Try again or pick another model."
    return None
