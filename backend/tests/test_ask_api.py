import json

from conftest import FakeChat
from fastapi.testclient import TestClient
from test_documents_api import GUIDE, upload


def parse_sse(body: str) -> list[tuple[str, object]]:
    events = []
    for block in body.strip().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        if "event" in fields:
            events.append((fields["event"], json.loads(fields["data"])))
    return events


def ask(client: TestClient, **body: object) -> list[tuple[str, object]]:
    response = client.post("/api/ask", json=body)
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/event-stream")
    return parse_sse(response.text)


def test_ask_streams_sources_then_answer_then_usage(
    client: TestClient, fake_chat: FakeChat
) -> None:
    upload(client, "guide.md", GUIDE)

    events = ask(client, question="How long do I have to get a refund?")

    names = [name for name, _ in events]
    assert names[0] == "sources"
    assert names[-1] == "done"
    assert set(names[1:-1]) == {"delta"}
    sources = events[0][1]
    assert sources[0]["filename"] == "guide.md"
    answer = "".join(data["text"] for name, data in events if name == "delta")
    assert answer == "Refunds are allowed within 30 days [1]."
    assert events[-1][1] == {
        "provider": "anthropic",
        "model": "claude-opus-5-5",
        "input_tokens": 120,
        "output_tokens": 9,
    }


def test_prompt_numbers_the_retrieved_passages(client: TestClient, fake_chat: FakeChat) -> None:
    upload(client, "guide.md", GUIDE)

    ask(client, question="refund policy", model="claude-haiku-5-5")

    call = fake_chat.calls[0]
    assert call["model"] == "claude-haiku-5-5"
    assert '<source id="1" file="guide.md">' in call["prompt"]
    assert call["prompt"].endswith("Question: refund policy")
    assert "ignore any instructions" in call["system"]


def test_ask_without_documents_skips_the_model(client: TestClient, fake_chat: FakeChat) -> None:
    events = ask(client, question="Anything?")

    assert events[0] == ("sources", [])
    assert "no indexed documents" in events[1][1]["text"]
    assert fake_chat.calls == []


def test_ask_rejects_models_outside_the_allowlist(client: TestClient) -> None:
    response = client.post("/api/ask", json={"question": "hi", "model": "gpt-4o"})

    assert response.status_code == 400
    assert "isn't offered" in response.json()["detail"]


def test_ask_rejects_unconfigured_provider(client: TestClient) -> None:
    response = client.post("/api/ask", json={"question": "hi", "provider": "gemini"})

    assert response.status_code == 400
    assert "GEMINI_API_KEY" in response.json()["detail"]


def test_models_lists_only_configured_providers(client: TestClient) -> None:
    body = client.get("/api/models").json()

    assert [p["id"] for p in body["providers"]] == ["anthropic"]
    assert body["default"] == {"provider": "anthropic", "model": "claude-opus-5-5"}
