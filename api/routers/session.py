from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query

from api import auth, customers, db
from api.contract_models import (
    CodeRequested,
    Config,
    CustomerSearchResults,
    OpenCustomerSessionRequest,
    RequestCustomerCode,
    Session,
)
from api.errors import invalid_body, not_found, unauthorized
from api.mail import Mailer, get_mailer
from api.settings import settings

router = APIRouter()


@router.get("/config", response_model=Config)
def read_config() -> Config:
    return Config(demo_login=settings.demo_login)


@router.get("/customers/search", response_model=CustomerSearchResults)
def search_customers(
    q: Annotated[str | None, Query(min_length=1)] = None,
    random: bool | None = None,
) -> CustomerSearchResults:
    if not settings.demo_login:
        raise not_found()
    if (q is None) == (random is None) or random is False:
        raise invalid_body()
    with db.connect() as conn:
        hits = customers.search(conn, q) if q is not None else customers.pick_random_with_email(conn)
    return CustomerSearchResults(customers=hits)


@router.post("/session/code", response_model=CodeRequested)
def request_customer_code(
    body: RequestCustomerCode,
    tasks: BackgroundTasks,
    mailer: Annotated[Mailer, Depends(get_mailer)],
) -> CodeRequested:
    with db.connect() as conn:
        delivery = auth.issue_customer_code(conn, settings.jwt_secret, body.document_number.strip(), _now())
    if delivery is not None:
        tasks.add_task(mailer.send_login_code, delivery.email, delivery.code)
    return CodeRequested(expires_in_seconds=int(auth.CODE_TTL.total_seconds()))


@router.post("/session", response_model=Session)
def open_customer_session(body: OpenCustomerSessionRequest) -> Session:
    now = _now()
    with db.connect() as conn:
        claims = auth.open_customer_session(conn, settings.jwt_secret, body.document_number.strip(), body.code, now)
    if claims is None:
        raise unauthorized()
    return Session(token=auth.issue_token(settings.jwt_secret, claims, now), sub=claims.sub, role=claims.role)


def _now() -> datetime:
    return datetime.now(UTC)
