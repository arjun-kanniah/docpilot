from collections.abc import Iterator

from fastapi.testclient import TestClient
from test_agent import Script, ScriptedModel, review, search, text
from test_ask_api import parse_sse
from test_documents_api import GUIDE, upload

from docpilot.agent.models import get_model_factory
from docpilot.followup import MAX_TURNS, conversation_block, standalone
from docpilot.llm.base import LLMError, Usage
from docpilot.llm.providers import LLMRegistry, get_llm_registry
from docpilot.main import app
from docpilot.schemas import TurnIn

WARRANTY = b"""# Warranty

Every station has a 2-year warranty. Registering within 30 days extends it to 3 years.
"""


class ScriptedChat:
    """A ChatModel that streams one scripted reply per call and records each call."""

    def __init__(self, *replies: str | Exception) -> None:
        self.replies = list(replies)
        self.calls: list[dict[str, str]] = []

    def stream(
        self, *, model: str, system: str, prompt: str, max_tokens: int
    ) -> Iterator[str | Usage]:
        self.calls.append({"system": system, "prompt": prompt})
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        yield reply
        yield Usage(10, 2)


def use_chat(chat: ScriptedChat) -> None:
    registry = LLMRegistry({"anthropic": chat}, default_provider="anthropic")
    app.dependency_overrides[get_llm_registry] = lambda: registry


HISTORY = [{"question": "How long is the warranty?", "answer": "Two years [1]."}]


def test_no_history_means_no_rewrite_call() -> None:
    chat = ScriptedChat()

    assert standalone(chat, "m", [], "How long is the warranty?") == (
        "How long is the warranty?",
        Usage(0, 0),
    )
    assert chat.calls == []


def test_rewrite_uses_the_conversation_and_falls_back_to_the_message() -> None:
    history = [TurnIn(**turn) for turn in HISTORY]
    chat = ScriptedChat('"How do I extend the warranty?"', "  ")

    assert standalone(chat, "m", history, "Can I extend it?")[0] == (
        "How do I extend the warranty?"
    )
    assert "User: How long is the warranty?" in chat.calls[0]["prompt"]
    assert chat.calls[0]["prompt"].endswith("Latest message: Can I extend it?")
    assert standalone(chat, "m", history, "Can I extend it?")[0] == "Can I extend it?"


def test_conversation_block_drops_citations_and_old_turns() -> None:
    turns = [TurnIn(question=f"q{i}", answer=f"a{i} [1][2] and [3, 4].") for i in range(10)]

    block = conversation_block(turns[-MAX_TURNS:])

    assert "User: q0" not in block and f"User: q{10 - MAX_TURNS}" in block
    assert "[" not in block.replace("<", "").replace(">", "")  # no citation markers
    assert "a9 and." in block


def test_a_follow_up_is_rewritten_searched_and_answered_with_context(
    client: TestClient,
) -> None:
    upload(client, "guide.md", GUIDE)
    upload(client, "warranty.md", WARRANTY)
    chat = ScriptedChat("How do I extend the station warranty?", "Register within 30 days [1].")
    use_chat(chat)

    response = client.post("/api/ask", json={"question": "Can I extend it?", "history": HISTORY})
    events = parse_sse(response.text)

    assert events[0] == ("rewrite", {"question": "How do I extend the station warranty?"})
    assert events[1][0] == "sources" and events[1][1][0]["filename"] == "warranty.md"
    answer_prompt = chat.calls[1]["prompt"]
    assert "<conversation>" in answer_prompt and "User: How long is the warranty?" in answer_prompt
    assert answer_prompt.endswith("Question: How do I extend the station warranty?")
    assert events[-1][1]["input_tokens"] == 20  # the rewrite and the answer


def test_a_failed_rewrite_falls_back_to_the_question(client: TestClient) -> None:
    upload(client, "warranty.md", WARRANTY)
    use_chat(ScriptedChat(LLMError("rate limited"), "Two years [1]."))

    response = client.post("/api/ask", json={"question": "Warranty length?", "history": HISTORY})
    events = parse_sse(response.text)

    assert events[0][0] == "sources"  # no rewrite event
    assert events[-1][0] == "done"


def test_ask_searches_only_the_chosen_documents(client: TestClient) -> None:
    upload(client, "guide.md", GUIDE)
    warranty_id = upload(client, "warranty.md", WARRANTY).json()["document"]["id"]
    use_chat(ScriptedChat("Answer [1]."))

    body = {"question": "refund policy", "document_ids": [warranty_id], "k": 20}
    events = parse_sse(client.post("/api/ask", json=body).text)

    assert {hit["filename"] for hit in events[0][1]} == {"warranty.md"}


def test_an_empty_document_selection_is_rejected(client: TestClient) -> None:
    response = client.post("/api/ask", json={"question": "anything", "document_ids": []})

    assert response.status_code == 422


def test_research_tools_see_only_the_chosen_documents(client: TestClient) -> None:
    upload(client, "guide.md", GUIDE)
    warranty_id = upload(client, "warranty.md", WARRANTY).json()["document"]["id"]
    list_docs = text("")
    list_docs.tool_calls = [{"name": "list_documents", "args": {}, "id": "l1"}]
    script = Script(
        list_docs, search("refunds", "c2"), text("- notes"), review(True), text("Done.")
    )
    app.dependency_overrides[get_model_factory] = lambda: (
        lambda provider, model, max_tokens: ScriptedModel(script=script)
    )

    body = {"task": "Explain refunds", "document_ids": [warranty_id]}
    events = parse_sse(client.post("/api/agent", json=body).text)

    tools = [data for name, data in events if name == "tool"]
    assert tools[0]["summary"] == "1 document"
    sources = next(data for name, data in events if name == "sources")
    assert {hit["filename"] for hit in sources} == {"warranty.md"}


def test_research_rewrites_a_follow_up_task(client: TestClient) -> None:
    upload(client, "warranty.md", WARRANTY)
    use_chat(ScriptedChat("Compare the warranty terms for registered stations."))
    script = Script(search("warranty"), text("- notes"), review(True), text("Done."))
    app.dependency_overrides[get_model_factory] = lambda: (
        lambda provider, model, max_tokens: ScriptedModel(script=script)
    )

    body = {"task": "And for registered ones?", "history": HISTORY}
    events = parse_sse(client.post("/api/agent", json=body).text)

    assert events[0] == (
        "rewrite",
        {"question": "Compare the warranty terms for registered stations."},
    )
    assert (
        script.calls[0][-1].content == "Task: Compare the warranty terms for registered stations."
    )
