from fastapi.testclient import TestClient

from docpilot import __version__
from docpilot.main import app

client = TestClient(app)


def test_health_reports_ok_and_version() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["version"] == __version__
