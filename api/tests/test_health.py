from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_ok(monkeypatch) -> None:
    monkeypatch.setattr("api.main.db.ping", lambda: None)
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_ready_not_ready(monkeypatch) -> None:
    def boom() -> None:
        raise RuntimeError("database down")

    monkeypatch.setattr("api.main.db.ping", boom)
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "error": "RuntimeError"}
