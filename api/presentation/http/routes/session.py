from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends

from api.contract_models import CodeRequested, OpenCustomerSessionRequest, RequestCustomerCode, Session
from api.domain.session.codes import CODE_TTL
from api.domain.session.tokens import issue_token
from api.infrastructure.mail.smtp import Mailer, get_mailer
from api.presentation.http.dependencies import (
    IssueCustomerCode,
    OpenCustomerSession,
    get_issue_customer_code,
    get_jwt_secret,
    get_now,
    get_open_customer_session,
)
from api.presentation.http.errors import unauthorized

router = APIRouter(prefix="/session")


@router.post("/code", response_model=CodeRequested)
def request_customer_code(
    body: RequestCustomerCode,
    tasks: BackgroundTasks,
    issue: Annotated[IssueCustomerCode, Depends(get_issue_customer_code)],
    mailer: Annotated[Mailer, Depends(get_mailer)],
) -> CodeRequested:
    delivery = issue(body.document_number.strip())
    if delivery is not None:
        tasks.add_task(mailer.send_login_code, delivery.email, delivery.code)
    return CodeRequested(expires_in_seconds=int(CODE_TTL.total_seconds()))


@router.post("", response_model=Session)
def open_session(
    body: OpenCustomerSessionRequest,
    open_customer: Annotated[OpenCustomerSession, Depends(get_open_customer_session)],
    secret: Annotated[str, Depends(get_jwt_secret)],
    now: Annotated[datetime, Depends(get_now)],
) -> Session:
    claims = open_customer(body.document_number.strip(), body.code)
    if claims is None:
        raise unauthorized()
    return Session(token=issue_token(secret, claims, now), sub=claims.sub, role=claims.role)
