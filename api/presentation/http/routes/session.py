from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends

from api.contract_models import (
    CodeRequested,
    OpenAgentSessionRequest,
    OpenCustomerSessionRequest,
    RequestAgentCode,
    RequestCustomerCode,
    Session,
)
from api.domain.session.codes import CODE_TTL, CodeDelivery
from api.domain.session.tokens import SessionClaims, issue_token
from api.infrastructure.mail.smtp import Mailer, get_mailer
from api.presentation.http.dependencies import (
    IssueAgentCode,
    IssueCustomerCode,
    OpenAgentSession,
    OpenCustomerSession,
    get_issue_agent_code,
    get_issue_customer_code,
    get_jwt_secret,
    get_now,
    get_open_agent_session,
    get_open_customer_session,
)
from api.presentation.http.errors import unauthorized

router = APIRouter(prefix="/session")
agent_router = APIRouter(prefix="/agent/session")


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


@agent_router.post("/code", response_model=CodeRequested)
def request_agent_code(
    body: RequestAgentCode,
    tasks: BackgroundTasks,
    issue: Annotated[IssueAgentCode, Depends(get_issue_agent_code)],
    mailer: Annotated[Mailer, Depends(get_mailer)],
) -> CodeRequested:
    return _code_requested(issue(body.email, body.employee_code), tasks, mailer)


@agent_router.post("", response_model=Session)
def open_agent_session(
    body: OpenAgentSessionRequest,
    open_agent: Annotated[OpenAgentSession, Depends(get_open_agent_session)],
    secret: Annotated[str, Depends(get_jwt_secret)],
    now: Annotated[datetime, Depends(get_now)],
) -> Session:
    return _session(open_agent(body.email, body.employee_code, body.code), secret, now)


def _code_requested(delivery: CodeDelivery | None, tasks: BackgroundTasks, mailer: Mailer) -> CodeRequested:
    if delivery is not None:
        tasks.add_task(mailer.send_login_code, delivery.email, delivery.code)
    return CodeRequested(expires_in_seconds=int(CODE_TTL.total_seconds()))


def _session(claims: SessionClaims | None, secret: str, now: datetime) -> Session:
    if claims is None:
        raise unauthorized()
    return Session(token=issue_token(secret, claims, now), sub=claims.sub, role=claims.role)
