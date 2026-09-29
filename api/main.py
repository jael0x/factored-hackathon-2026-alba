from fastapi import FastAPI, Response, status

from api import db
from api.contract_models import Health, ReadyDown, ReadyOk

app = FastAPI(title="Alba", docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/health", response_model=Health)
def health() -> Health:
    return Health(status="ok")


@app.get("/ready", response_model=ReadyOk | ReadyDown)
def ready(response: Response) -> ReadyOk | ReadyDown:
    try:
        db.ping()
    except Exception as exc:  # noqa: BLE001 - surface readiness failure
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadyDown(status="not_ready", error=type(exc).__name__)
    return ReadyOk(status="ready")
