def friendly_error(exc: Exception) -> str | None:
    """A message safe to show users for a provider failure, or None if it isn't one."""
    import anthropic  # SDK imports are deferred until first use
    import openai
    from google.genai import errors as genai_errors

    if isinstance(exc, anthropic.AuthenticationError | openai.AuthenticationError):
        return "The provider rejected the API key."
    if isinstance(exc, anthropic.RateLimitError | openai.RateLimitError):
        return "The provider's rate limit was reached. Try again shortly."
    if isinstance(exc, anthropic.APIStatusError | openai.APIStatusError):
        return (
            f"The provider returned an error ({exc.status_code}). Try again or pick another model."
        )
    if isinstance(exc, anthropic.APIConnectionError | openai.APIConnectionError):
        return "Could not reach the provider."
    if isinstance(exc, genai_errors.APIError):
        if exc.code == 429:
            return "Gemini quota reached for this model. Try again later or pick another model."
        return f"Gemini returned an error ({exc.code}). Try again or pick another model."
    return None
