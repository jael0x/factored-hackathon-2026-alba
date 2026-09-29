from fastapi import FastAPI, Response, status

from api import db

app = FastAPI(title="Alba")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready(response: Response) -> dict[str, str]:
    try:
        db.ping()
    except Exception as exc:  # noqa: BLE001 - surface readiness failure
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "error": type(exc).__name__}
    return {"status": "ready"}
