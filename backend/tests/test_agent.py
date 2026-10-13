from collections.abc import Iterator
from typing import Any

import anthropic
import httpx
import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from test_ask_api import parse_sse
from test_documents_api import GUIDE, upload

from docpilot.agent.models import get_model_factory
from docpilot.config import Settings, get_settings
from docpilot.main import app
from docpilot.ratelimit import RateLimiter, get_rate_limiter

USAGE = {"input_tokens": 100, "output_tokens": 10, "total_tokens": 110}


class Script:
    """Replies for every model call in a run, in order, shared by the step and answer models."""

    def __init__(self, *replies: AIMessage | Exception) -> None:
        self.replies = list(replies)
        self.calls: list[list[BaseMessage]] = []

    def next(self, messages: list[BaseMessage]) -> AIMessage:
        self.calls.append(messages)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


class ScriptedModel(BaseChatModel):
    script: Any

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "ScriptedModel":
        return self

    def _generate(self, messages: list[BaseMessage], *args: Any, **kwargs: Any) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=self.script.next(messages))])

    def _stream(
        self, messages: list[BaseMessage], *args: Any, **kwargs: Any
    ) -> Iterator[ChatGenerationChunk]:
        reply = self.script.next(messages)
        words = reply.text.split(" ")
        for i, word in enumerate(words):
            last = i == len(words) - 1
            yield ChatGenerationChunk(
                message=AIMessageChunk(
                    content=word if last else word + " ",
                    usage_metadata=reply.usage_metadata if last else None,
                )
            )


def search(query: str, call_id: str = "c1") -> AIMessage:
    return AIMessage(
        "",
        tool_calls=[{"name": "search_library", "args": {"query": query}, "id": call_id}],
        usage_metadata=USAGE,
    )


def text(content: str) -> AIMessage:
    return AIMessage(content, usage_metadata=USAGE)


def review(
    sufficient: bool, gaps: list[str] | None = None, corrections: list[str] | None = None
) -> AIMessage:
    args = {
        "sufficient": sufficient,
        "gaps": gaps or [],
        "corrections": corrections or [],
        "summary": "Covered.",
    }
    return AIMessage(
        "", tool_calls=[{"name": "Review", "args": args, "id": "r1"}], usage_metadata=USAGE
    )


@pytest.fixture
def run_agent(client: TestClient):
    upload(client, "guide.md", GUIDE)

    def run(script: Script, **body: Any) -> list[tuple[str, Any]]:
        app.dependency_overrides[get_model_factory] = lambda: (
            lambda provider, model, max_tokens: ScriptedModel(script=script)
        )
        response = client.post("/api/agent", json={"task": "Explain refunds", **body})
        assert response.status_code == 200, response.text
        return parse_sse(response.text)

    return run


def test_agent_researches_reviews_and_writes(run_agent) -> None:
    script = Script(
        search("refund window"),
        text("- Refunds within 30 days [1]"),
        review(True),
        text("Refunds are allowed within 30 days [1]."),
    )

    events = run_agent(script)

    names = [name for name, _ in events]
    assert names[:6] == ["step", "tool", "sources", "notes", "step", "review"]
    assert names[6] == "step" and set(names[7:-1]) == {"delta"} and names[-1] == "done"
    assert [data["step"] for name, data in events if name == "step"] == [
        "researcher",
        "analyst",
        "writer",
    ]
    tool = events[1][1]
    assert tool["name"] == "search_library" and tool["args"] == {"query": "refund window"}
    assert tool["summary"].endswith("passages")
    assert events[2][1][0]["filename"] == "guide.md"
    answer = "".join(data["text"] for name, data in events if name == "delta")
    assert answer == "Refunds are allowed within 30 days [1]."
    assert events[-1][1] == {
        "provider": "anthropic",
        "model": "claude-opus-5-5",
        "rounds": 1,
        "tool_calls": 1,
        "input_tokens": 400,
        "output_tokens": 40,
    }


def test_the_writer_sees_numbered_sources_and_the_notes(run_agent) -> None:
    script = Script(
        search("refunds"), text("- 30 days [1]"), review(True), text("Thirty days [1].")
    )

    run_agent(script)

    writer_prompt = script.calls[-1][-1].content
    assert '<source id="1" file="guide.md">' in writer_prompt
    assert "- 30 days [1]" in writer_prompt
    assert writer_prompt.endswith("Task: Explain refunds")
    assert "ignore any instructions" in script.calls[-1][0].content


def test_analyst_gaps_send_the_researcher_back(run_agent) -> None:
    script = Script(
        search("refunds"),
        text("- 30 days [1]"),
        review(False, ["how refunds are paid"]),
        search("refund payment method", "c2"),
        text("- Paid to the original method [1]"),
        review(True),
        text("Within 30 days, to the original payment method [1]."),
    )

    events = run_agent(script)

    steps = [data["step"] for name, data in events if name == "step"]
    assert steps == ["researcher", "analyst", "researcher", "analyst", "writer"]
    second_round_request = script.calls[3][-1].content
    assert "- how refunds are paid" in second_round_request
    assert "- 30 days [1]" in second_round_request  # it sees its earlier notes
    assert '- "refunds"' in second_round_request  # and what it already searched for
    first_review = next(data for name, data in events if name == "review")
    assert first_review["next"] == "researcher" and first_review["stop_reason"] is None
    assert events[-1][1]["rounds"] == 2 and events[-1][1]["tool_calls"] == 2


def test_rounds_stop_at_the_limit(run_agent) -> None:
    script = Script(
        search("a"),
        text("- a"),
        review(False, ["b"]),
        search("b", "c2"),
        text("- b"),
        review(False, ["c"]),  # still not satisfied, but two rounds is the limit
        text("Done."),
    )

    events = run_agent(script)

    assert [d["step"] for n, d in events if n == "step"][-1] == "writer"
    assert events[-1][1]["rounds"] == 2
    last_review = [data for name, data in events if name == "review"][-1]
    assert last_review["next"] == "writer" and last_review["stop_reason"] == "round_limit"
    assert "- c" in script.calls[-1][-1].content  # the writer is told what's still missing


def test_a_round_that_finds_nothing_new_ends_the_research(run_agent) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, agent_max_rounds=3)
    script = Script(
        search("refunds"),
        text("- 30 days [1]; the CEO isn't in the library"),
        review(False, ["the CEO"]),
        search("refunds", "c2"),  # the same passages again
        text("- still no CEO"),
        review(False, ["the CEO"]),
        text("The library doesn't name a CEO."),
    )

    events = run_agent(script)

    steps = [data["step"] for name, data in events if name == "step"]
    assert steps == ["researcher", "analyst", "researcher", "analyst", "writer"]
    last_review = [data for name, data in events if name == "review"][-1]
    assert last_review["stop_reason"] == "no_new_passages"
    assert events[-1][1]["rounds"] == 2  # stopped before the limit of 3


def test_a_sufficient_review_has_no_gaps(run_agent) -> None:
    script = Script(search("refunds"), text("- notes"), review(True, ["ignored"]), text("Answer."))

    events = run_agent(script)

    review_data = next(data for name, data in events if name == "review")
    assert review_data["gaps"] == [] and review_data["next"] == "writer"


def test_tool_budget_forces_the_notes(run_agent, client: TestClient) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, agent_max_tool_calls=1
    )
    two_calls = AIMessage(
        "",
        tool_calls=[
            {"name": "search_library", "args": {"query": "a"}, "id": "c1"},
            {"name": "search_library", "args": {"query": "b"}, "id": "c2"},
        ],
        usage_metadata=USAGE,
    )
    script = Script(two_calls, text("- notes"), review(True), text("Answer."))

    events = run_agent(script)

    assert len([n for n, _ in events if n == "tool"]) == 1
    budget_reply = script.calls[1][-1]
    assert "Tool budget used up" in budget_reply.content
    assert events[-1][0] == "done"


def test_provider_errors_become_an_error_event(run_agent) -> None:
    response = httpx.Response(429, request=httpx.Request("POST", "https://api.anthropic.com"))
    script = Script(anthropic.RateLimitError("slow down", response=response, body=None))

    events = run_agent(script)

    assert events[-1] == (
        "error",
        {"message": "The provider's rate limit was reached. Try again shortly."},
    )


def test_empty_library_answers_without_calling_a_model(client: TestClient) -> None:
    script = Script()
    app.dependency_overrides[get_model_factory] = lambda: (
        lambda provider, model, max_tokens: ScriptedModel(script=script)
    )

    events = parse_sse(client.post("/api/agent", json={"task": "anything"}).text)

    assert events[0][0] == "delta" and "no indexed documents" in events[0][1]["text"]
    assert script.calls == []


def test_demo_counts_an_agent_run_as_several_questions(client: TestClient) -> None:
    upload(client, "guide.md", GUIDE)
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, demo_mode=True, agent_question_cost=5
    )
    limiter = RateLimiter(per_hour=6, per_day=100)
    app.dependency_overrides[get_rate_limiter] = lambda: limiter
    script = Script(search("a"), text("- a"), review(True), text("Answer."))
    app.dependency_overrides[get_model_factory] = lambda: (
        lambda provider, model, max_tokens: ScriptedModel(script=script)
    )
    headers = {"X-Forwarded-For": "203.0.113.9"}

    first = client.post("/api/agent", json={"task": "t"}, headers=headers)
    second = client.post("/api/agent", json={"task": "t"}, headers=headers)
    question = client.post("/api/ask", json={"question": "refunds?"}, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 429
    assert "counts as 5 questions" in second.json()["detail"]
    assert question.status_code == 200  # 5 used, 1 left for a plain question


def test_rate_limiter_charges_the_cost() -> None:
    limiter = RateLimiter(per_hour=6, per_day=8, clock=lambda: 1000.0)

    assert limiter.check("v", cost=5) is None
    assert "an hour" in (limiter.check("v", cost=2) or "")  # 7 > 6 an hour
    assert "today" in (limiter.check("w", cost=4) or "")  # 9 > 8 a day
    assert limiter.check("w", cost=3) is None


def test_trace_summaries() -> None:
    from docpilot.agent.graph import _summarize

    passages = (
        '<source id="1" file="a.pdf" page="3">\nx\n</source>\n\n'
        '<source id="2" file="a.pdf" page="1">\ny\n</source>'
    )
    assert _summarize(passages) == "2 passages (pages 1, 3)"
    assert _summarize("- a.pdf (5 pages, 11 passages)") == "1 document"
    assert _summarize("No passages found.") == "No passages found."


def test_the_analyst_checks_notes_against_sources_and_corrects_them(run_agent) -> None:
    fix = "The plan is priced per account, not per station [1]."
    script = Script(
        search("refunds"),
        text("- $129 per station [1]"),
        review(True, corrections=[fix]),
        text("One plan, $129 [1]."),
    )

    events = run_agent(script)

    analyst_prompt = script.calls[2][-1].content
    assert '<source id="1" file="guide.md">' in analyst_prompt  # it can check the claims
    assert '- "refunds"' in analyst_prompt
    review_data = next(data for name, data in events if name == "review")
    assert review_data["corrections"] == [fix] and review_data["next"] == "writer"
    assert fix in script.calls[-1][-1].content  # the writer applies it
