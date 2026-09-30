from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response, status

from api import db
from api.contract_models import Health, ReadyDown, ReadyOk
from api.errors import install_error_handlers
from api.routers import customer, session
from api.settings import require_jwt_secret, settings


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    require_jwt_secret(settings.jwt_secret)
    yield


app = FastAPI(title="Alba", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
install_error_handlers(app)
app.include_router(session.router)
app.include_router(customer.router)


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
