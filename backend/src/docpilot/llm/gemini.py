from collections.abc import Iterator

from google import genai
from google.genai import errors, types

from docpilot.llm.base import LLMError, Usage


class GeminiChat:
    """Gemini via the official Google GenAI SDK."""

    def __init__(self, api_key: str) -> None:
        # Retry rate limits and overloads with backoff (about 15s at most): the free tier allows
        # only a few requests a minute, and busy models return 503 now and then.
        retry = types.HttpRetryOptions(attempts=4, initial_delay=2.0, max_delay=30.0)
        self._client = genai.Client(
            api_key=api_key, http_options=types.HttpOptions(retry_options=retry)
        )

    def stream(
        self, *, model: str, system: str, prompt: str, max_tokens: int
    ) -> Iterator[str | Usage]:
        config = types.GenerateContentConfig(
            system_instruction=system, max_output_tokens=max_tokens
        )
        usage = Usage(0, 0)
        try:
            for chunk in self._client.models.generate_content_stream(
                model=model, contents=prompt, config=config
            ):
                if chunk.text:
                    yield chunk.text
                if meta := chunk.usage_metadata:
                    output = (meta.candidates_token_count or 0) + (meta.thoughts_token_count or 0)
                    usage = Usage(meta.prompt_token_count or 0, output)
        except errors.APIError as exc:
            raise LLMError(_message(exc)) from exc
        yield usage


def _message(exc: errors.APIError) -> str:
    if exc.code in (401, 403):
        return "Google rejected the API key. Check GEMINI_API_KEY."
    if exc.code == 429:
        return "Gemini quota reached for this model. Try again later or pick another model."
    if exc.code == 503:
        return "This Gemini model is overloaded right now. Try again or pick another model."
    return f"Gemini API error ({exc.code}): {exc.message}"
