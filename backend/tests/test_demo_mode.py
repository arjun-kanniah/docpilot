import pytest
from conftest import FakeChat
from fastapi.testclient import TestClient
from starlette.requests import Request
from test_documents_api import GUIDE, upload

from docpilot.config import Settings, get_settings
from docpilot.llm.providers import LLMRegistry, get_llm_registry
from docpilot.main import app
from docpilot.ratelimit import HOUR, RateLimiter, get_rate_limiter, visitor_id


@pytest.fixture
def demo(client: TestClient, fake_chat: FakeChat) -> TestClient:
    """The API as the public demo runs it: indexed docs, read-only, cheap models, limits."""
    document_id = upload(client, "guide.md", GUIDE).json()["document"]["id"]
    settings = Settings(_env_file=None, demo_mode=True, answer_top_k=3)
    registry = LLMRegistry(
        {"anthropic": fake_chat, "openai": FakeChat()},
        default_provider="anthropic",
        default_model="claude-opus-5-5",
        allowed=["claude-haiku-5-5", "gpt-6-luna"],
    )
    limiter = RateLimiter(per_hour=2, per_day=100)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_llm_registry] = lambda: registry
    app.dependency_overrides[get_rate_limiter] = lambda: limiter
    client.document_id = document_id  # type: ignore[attr-defined]
    return client


def test_demo_library_is_read_only(demo: TestClient) -> None:
    assert upload(demo, "notes.md", b"# Notes\n\nSomething new.").status_code == 403
    delete = demo.delete(f"/api/documents/{demo.document_id}")  # type: ignore[attr-defined]
    assert delete.status_code == 403
    assert "read-only" in delete.json()["detail"]
    assert len(demo.get("/api/documents").json()) == 1


def test_demo_offers_only_allowed_models(demo: TestClient) -> None:
    body = demo.get("/api/models").json()

    assert [(p["id"], p["models"]) for p in body["providers"]] == [
        ("anthropic", ["claude-haiku-5-5"]),
        ("openai", ["gpt-6-luna"]),
    ]
    # The configured default (Opus) isn't allowed, so the provider's first allowed model wins
    assert body["default"] == {"provider": "anthropic", "model": "claude-haiku-5-5"}
    denied = demo.post("/api/ask", json={"question": "refunds?", "model": "claude-opus-5-5"})
    assert denied.status_code == 400


def test_demo_rate_limits_questions_per_visitor(demo: TestClient, fake_chat: FakeChat) -> None:
    ask = {"question": "How long do I have to get a refund?", "k": 20}
    headers = {"X-Forwarded-For": "203.0.113.9"}

    assert demo.post("/api/ask", json=ask, headers=headers).status_code == 200
    assert demo.post("/api/ask", json=ask, headers=headers).status_code == 200
    limited = demo.post("/api/ask", json=ask, headers=headers)
    other_visitor = demo.post("/api/ask", json=ask, headers={"X-Forwarded-For": "198.51.100.4"})

    assert limited.status_code == 429
    assert "2 questions an hour" in limited.json()["detail"]
    assert other_visitor.status_code == 200
    assert fake_chat.calls[0]["prompt"].count("<source ") <= 3  # k clamped to answer_top_k


def test_health_reports_demo_mode(demo: TestClient) -> None:
    assert demo.get("/api/health").json()["demo"] is True


def test_rate_limiter_windows() -> None:
    now = [1_000_000.0]
    limiter = RateLimiter(per_hour=2, per_day=3, clock=lambda: now[0])

    assert limiter.check("a") is None
    assert limiter.check("a") is None
    assert limiter.check("a") is not None  # hourly limit
    now[0] += HOUR
    assert limiter.check("a") is None  # window moved on
    assert "today" in (limiter.check("b") or "")  # daily cap of 3 reached


def test_visitor_id_uses_the_last_forwarded_address() -> None:
    scope = {
        "type": "http",
        "headers": [(b"x-forwarded-for", b"6.6.6.6, 203.0.113.9")],
        "client": ("10.0.0.1", 1234),
    }

    assert visitor_id(Request(scope)) == "203.0.113.9"


def test_visitor_id_trusts_the_worker_only_with_the_secret() -> None:
    def request(secret: str) -> Request:
        headers = [
            (b"x-forwarded-for", b"203.0.113.9, 104.16.0.1"),
            (b"x-docpilot-client-ip", b"198.51.100.7"),
            (b"x-docpilot-proxy-secret", secret.encode()),
        ]
        return Request({"type": "http", "headers": headers, "client": ("10.0.0.1", 1234)})

    assert visitor_id(request("s3cret"), proxy_secret="s3cret") == "198.51.100.7"
    assert visitor_id(request("guess"), proxy_secret="s3cret") == "104.16.0.1"
    assert visitor_id(request(""), proxy_secret="") == "104.16.0.1"  # no secret configured
