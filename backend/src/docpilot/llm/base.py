from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol


class LLMError(Exception):
    """A provider failure, with a message that is safe to show to users."""


@dataclass(frozen=True)
class Usage:
    input_tokens: int
    output_tokens: int


class ChatModel(Protocol):
    def stream(
        self, *, model: str, system: str, prompt: str, max_tokens: int
    ) -> Iterator[str | Usage]:
        """Yield answer text as it is generated, then one final `Usage`.

        Raises `LLMError` for failures the user should see.
        """
        ...
