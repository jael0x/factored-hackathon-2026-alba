import pytest
from fastapi.testclient import TestClient

from api.main import app


def test_health_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("api.presentation.http.routes.health.ping", lambda _pool: None)
    with TestClient(app) as client:
        response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_ready_not_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(_pool: object) -> None:
        raise RuntimeError("database down")

    monkeypatch.setattr("api.presentation.http.routes.health.ping", boom)
    with TestClient(app) as client:
        response = client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "error": "RuntimeError"}
