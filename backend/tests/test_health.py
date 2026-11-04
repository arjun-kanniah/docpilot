import pytest
from fastapi.testclient import TestClient

from docpilot import __version__, main
from docpilot.config import Settings
from docpilot.main import app

client = TestClient(app)


def test_health_reports_ok_and_version() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["version"] == __version__


class RecordingEmbedder:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def embed_query(self, text: str) -> list[float]:
        self.queries.append(text)
        return []


@pytest.mark.parametrize("preload", [True, False])
def test_startup_preloads_the_embedder_only_when_asked(
    monkeypatch: pytest.MonkeyPatch, preload: bool
) -> None:
    embedder = RecordingEmbedder()
    monkeypatch.setattr(main, "get_settings", lambda: Settings(preload_embedder=preload))
    monkeypatch.setattr(main, "get_embedder", lambda: embedder)

    with TestClient(app):  # entering runs the startup hook
        pass

    assert len(embedder.queries) == (1 if preload else 0)
