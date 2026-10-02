from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends

from api.contract_models import (
    CodeRequested,
    OpenConsultantSessionRequest,
    OpenCustomerSessionRequest,
    RequestConsultantCode,
    RequestCustomerCode,
    Session,
)
from api.domain.session.codes import CODE_TTL_SECONDS, CodeDelivery
from api.domain.session.tokens import SessionClaims, issue_token
from api.infrastructure.mail.smtp import Mailer, get_mailer
from api.presentation.http.dependencies import (
    IssueConsultantCode,
    IssueCustomerCode,
    OpenConsultantSession,
    OpenCustomerSession,
    get_issue_consultant_code,
    get_issue_customer_code,
    get_jwt_secret,
    get_now,
    get_open_consultant_session,
    get_open_customer_session,
)
from api.presentation.http.errors import unauthorized

router = APIRouter(prefix="/session")
consultant_router = APIRouter(prefix="/consultant/session")


@router.post("/code", response_model=CodeRequested)
def request_customer_code(
    body: RequestCustomerCode,
    tasks: BackgroundTasks,
    issue: Annotated[IssueCustomerCode, Depends(get_issue_customer_code)],
    mailer: Annotated[Mailer, Depends(get_mailer)],
) -> CodeRequested:
    return _code_requested(issue(body.document_number.strip()), tasks, mailer)


@router.post("", response_model=Session)
def open_session(
    body: OpenCustomerSessionRequest,
    open_customer: Annotated[OpenCustomerSession, Depends(get_open_customer_session)],
    secret: Annotated[str, Depends(get_jwt_secret)],
    now: Annotated[datetime, Depends(get_now)],
) -> Session:
    return _session(open_customer(body.document_number.strip(), body.code), secret, now)


@consultant_router.post("/code", response_model=CodeRequested)
def request_consultant_code(
    body: RequestConsultantCode,
    tasks: BackgroundTasks,
    issue: Annotated[IssueConsultantCode, Depends(get_issue_consultant_code)],
    mailer: Annotated[Mailer, Depends(get_mailer)],
) -> CodeRequested:
    return _code_requested(issue(body.email, body.employee_code), tasks, mailer)


@consultant_router.post("", response_model=Session)
def open_consultant_session(
    body: OpenConsultantSessionRequest,
    open_consultant: Annotated[OpenConsultantSession, Depends(get_open_consultant_session)],
    secret: Annotated[str, Depends(get_jwt_secret)],
    now: Annotated[datetime, Depends(get_now)],
) -> Session:
    return _session(open_consultant(body.email, body.employee_code, body.code), secret, now)


def _code_requested(delivery: CodeDelivery | None, tasks: BackgroundTasks, mailer: Mailer) -> CodeRequested:
    if delivery is not None:
        tasks.add_task(mailer.send_login_code, delivery.email, delivery.code)
    return CodeRequested(expires_in_seconds=CODE_TTL_SECONDS)


def _session(claims: SessionClaims | None, secret: str, now: datetime) -> Session:
    if claims is None:
        raise unauthorized()
    return Session(token=issue_token(secret, claims, now), sub=claims.sub, role=claims.role)
