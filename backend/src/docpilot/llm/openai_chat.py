from collections.abc import Iterator

import openai

from docpilot.llm.base import LLMError, Usage


class OpenAIChat:
    """OpenAI models via the official SDK's Responses API."""

    def __init__(self, api_key: str) -> None:
        self._client = openai.OpenAI(api_key=api_key)

    def stream(
        self, *, model: str, system: str, prompt: str, max_tokens: int
    ) -> Iterator[str | Usage]:
        refused = False
        try:
            with self._client.responses.stream(
                model=model,
                instructions=system,
                input=prompt,
                max_output_tokens=max_tokens,
                store=False,  # don't keep document passages on OpenAI's side
            ) as stream:
                for event in stream:
                    if event.type == "response.output_text.delta":
                        yield event.delta
                    elif event.type == "response.refusal.done":
                        refused = True
                response = stream.get_final_response()
        except openai.AuthenticationError as exc:
            raise LLMError("OpenAI rejected the API key. Check OPENAI_API_KEY.") from exc
        except openai.RateLimitError as exc:
            raise LLMError("OpenAI rate limit or quota reached. Try again shortly.") from exc
        except openai.APIStatusError as exc:
            raise LLMError(f"OpenAI API error ({exc.status_code}): {exc.message}") from exc
        except openai.APIConnectionError as exc:
            raise LLMError("Could not reach the OpenAI API.") from exc

        if refused:
            raise LLMError("The model declined to answer this question.")
        if response.status == "incomplete":
            reason = response.incomplete_details.reason if response.incomplete_details else None
            if reason == "content_filter":
                raise LLMError("The answer was blocked by OpenAI's content filter.")
            yield "\n\n[Answer cut off at the length limit.]"
        usage = response.usage
        yield Usage(usage.input_tokens, usage.output_tokens) if usage else Usage(0, 0)
