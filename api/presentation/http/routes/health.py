from fastapi import APIRouter, Request, Response, status

from api.contract_models import Health, ReadyDown, ReadyOk
from api.infrastructure.db.pool import ping

router = APIRouter()


@router.get("/health", response_model=Health)
def health() -> Health:
    return Health(status="ok")


@router.get("/ready", response_model=ReadyOk | ReadyDown)
def ready(response: Response, request: Request) -> ReadyOk | ReadyDown:
    try:
        ping(request.app.state.pool)
    except Exception as exc:  # noqa: BLE001 - the ready body names the failure type
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadyDown(status="not_ready", error=type(exc).__name__)
    return ReadyOk(status="ready")
