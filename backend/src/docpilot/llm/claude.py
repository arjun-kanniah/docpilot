from collections.abc import Iterator

import anthropic

from docpilot.llm.base import LLMError, Usage


class ClaudeChat:
    """Claude via the official Anthropic SDK."""

    def __init__(self, api_key: str) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)

    def stream(
        self, *, model: str, system: str, prompt: str, max_tokens: int
    ) -> Iterator[str | Usage]:
        try:
            with self._client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                yield from stream.text_stream
                message = stream.get_final_message()
        except anthropic.AuthenticationError as exc:
            raise LLMError("Anthropic rejected the API key. Check ANTHROPIC_API_KEY.") from exc
        except anthropic.RateLimitError as exc:
            raise LLMError("Anthropic rate limit reached. Try again shortly.") from exc
        except anthropic.APIStatusError as exc:
            raise LLMError(f"Anthropic API error ({exc.status_code}): {exc.message}") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError("Could not reach the Anthropic API.") from exc

        if message.stop_reason == "refusal":
            raise LLMError("The model declined to answer this question.")
        if message.stop_reason == "max_tokens":
            yield "\n\n[Answer cut off at the length limit.]"
        yield Usage(message.usage.input_tokens, message.usage.output_tokens)
