"""Follow-up questions: turn a message that leans on the conversation into one that stands alone.

Retrieval searches for the standalone version, since "what about the Max?" alone finds nothing
useful. The earlier turns also go into the answer prompt, as context for what the user means.
"""

import re
from collections.abc import Sequence
from typing import Protocol

from docpilot.llm.base import ChatModel, Usage

MAX_TURNS = 6  # earlier turns used as context; older ones are dropped
ANSWER_CHARS = 1500  # each earlier answer is cut to this length

CONDENSE_PROMPT = """\
You rewrite the user's latest message in a conversation about their documents so that it \
stands alone: someone who hasn't seen the conversation should understand it fully.

- Replace words like "it", "that one" or "the same" with what they refer to, and carry over \
conditions the user set earlier (a site, a budget, a number of stations).
- Keep it short and in the user's words: a question to search with, not a summary. Don't \
copy facts or figures from earlier answers, don't answer it, and don't add requests the \
user didn't make.
- If it already stands alone, return it unchanged.

Reply with the rewritten message only."""

_CITATIONS = re.compile(r"\s?\[\d+(?:\s*,\s*\d+)*\]")


class Turn(Protocol):
    question: str
    answer: str


def recent(history: Sequence[Turn]) -> list[Turn]:
    return list(history[-MAX_TURNS:])


def conversation_block(history: Sequence[Turn]) -> str:
    """Earlier turns for a prompt. Citation markers are dropped: they pointed at old sources."""
    turns = []
    for turn in recent(history):
        answer = _CITATIONS.sub("", turn.answer).strip()
        if len(answer) > ANSWER_CHARS:
            answer = answer[:ANSWER_CHARS].rstrip() + " […]"
        turns.append(f"<turn>\nUser: {turn.question}\nAssistant: {answer}\n</turn>")
    return "<conversation>\n" + "\n".join(turns) + "\n</conversation>"


def standalone(
    chat: ChatModel, model: str, history: Sequence[Turn], message: str
) -> tuple[str, Usage]:
    """The message rewritten to stand alone, and the tokens that took. No history: no call."""
    if not history:
        return message, Usage(0, 0)
    parts: list[str] = []
    usage = Usage(0, 0)
    for item in chat.stream(
        model=model,
        system=CONDENSE_PROMPT,
        prompt=f"{conversation_block(history)}\n\nLatest message: {message}",
        max_tokens=1000,
    ):
        if isinstance(item, Usage):
            usage = item
        else:
            parts.append(item)
    rewritten = "".join(parts).strip().strip('"').strip()
    return (rewritten[:2000] or message), usage
