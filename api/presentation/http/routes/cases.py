from typing import Annotated
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Request
from psycopg_pool import ConnectionPool

from api.application.cases import (
    CaseNotAppealable,
    CaseView,
    appeal_customer_case,
    list_customer_cases,
    read_customer_case,
)
from api.application.processes import (
    CaseAlreadyOpen,
    CaseEnded,
    CaseNotFound,
    InCase,
    MessageTarget,
    StartCase,
    record_customer_message,
)
from api.contract_models import (
    AppealRequest,
    Case,
    CaseList,
    CaseSummary,
    Certificate,
    SendMessageRequest,
)
from api.domain.process.case import CaseRow, CertificateView
from api.domain.process.new_events import IdempotencyConflict
from api.domain.session.tokens import SessionClaims
from api.infrastructure.db.cases import PostgresThreads
from api.infrastructure.db.commands import PostgresCommands
from api.infrastructure.db.events import PostgresEventLog
from api.infrastructure.db.processes import PostgresProcesses
from api.presentation.http.cycle import planning, require_settled
from api.presentation.http.dependencies import get_connection, require_customer
from api.presentation.http.errors import (
    case_already_open,
    case_ended,
    case_not_appealable,
    invalid_body,
    message_id_reused,
    not_found,
)
from api.presentation.http.thread import wire_thread
from api.presentation.http.wire_numbers import wire_optional_number

router = APIRouter()

Refusal = IdempotencyConflict | CaseAlreadyOpen | CaseEnded | CaseNotFound | CaseNotAppealable


# The write and the read each take a pooled connection; none is held while the worker runs the cycle.
@router.post("/messages", response_model=Case)
def send_message(
    body: SendMessageRequest, request: Request, session: Annotated[SessionClaims, Depends(require_customer)]
) -> Case:
    target = message_target(body)
    pool: ConnectionPool = request.app.state.pool
    with pool.connection() as conn:
        try:
            sent = record_customer_message(
                planning(conn),
                PostgresProcesses(conn),
                session.sub,
                body.text,
                body.client_message_id,
                body.locale,
                target,
            )
        except (IdempotencyConflict, CaseAlreadyOpen, CaseEnded, CaseNotFound) as refused:
            conn.rollback()
            raise refusal(refused) from None
    require_settled(request, sent.event_id)
    with pool.connection() as conn:
        process_id = PostgresEventLog(conn).process_named_by(sent.event_id)
        if process_id is None:
            raise start_without_case(conn, sent.event_id, target)
        return case_or_not_found(conn, session.sub, process_id)


@router.get("/cases", response_model=CaseList)
def list_cases(
    session: Annotated[SessionClaims, Depends(require_customer)],
    conn: Annotated[psycopg.Connection, Depends(get_connection)],
) -> CaseList:
    return CaseList(cases=[wire_summary(case) for case in list_customer_cases(PostgresProcesses(conn), session.sub)])


@router.post("/case/{process_id}/appeal", response_model=Case)
def appeal_case(
    process_id: UUID,
    body: AppealRequest,
    request: Request,
    session: Annotated[SessionClaims, Depends(require_customer)],
) -> Case:
    pool: ConnectionPool = request.app.state.pool
    with pool.connection() as conn:
        try:
            appealed = appeal_customer_case(
                planning(conn), PostgresProcesses(conn), PostgresThreads(conn), session.sub, process_id, body.locale
            )
        except (CaseNotFound, CaseNotAppealable, CaseAlreadyOpen) as refused:
            conn.rollback()
            raise refusal(refused) from None
    if appealed is not None:
        require_settled(request, appealed.event_id)
    with pool.connection() as conn:
        return case_or_not_found(conn, session.sub, process_id)


@router.get("/case/{process_id}", response_model=Case)
def read_case(
    process_id: UUID,
    session: Annotated[SessionClaims, Depends(require_customer)],
    conn: Annotated[psycopg.Connection, Depends(get_connection)],
) -> Case:
    return case_or_not_found(conn, session.sub, process_id)


# Exactly one of product (a start from the home's dialog) and process_id (a message in that case), D24.
def message_target(body: SendMessageRequest) -> MessageTarget:
    if body.product is not None and body.process_id is None:
        return StartCase(body.product)
    if body.process_id is not None and body.product is None:
        return InCase(body.process_id)
    raise invalid_body()


def refusal(refused: Refusal) -> Exception:
    if isinstance(refused, CaseAlreadyOpen):
        return case_already_open()
    if isinstance(refused, CaseEnded):
        return case_ended()
    if isinstance(refused, CaseNotFound):
        return not_found()
    if isinstance(refused, CaseNotAppealable):
        return case_not_appealable()
    return message_id_reused()


# A settled start that opened no case lost to another start for its product (D24), unless its own command failed.
def start_without_case(conn: psycopg.Connection, event_id: UUID, target: MessageTarget) -> Exception:
    if isinstance(target, StartCase) and not PostgresCommands(conn).failed_for(event_id):
        return case_already_open()
    return LookupError(f"message {event_id} opened no case and joined none")


def case_or_not_found(conn: psycopg.Connection, customer_id: str, process_id: UUID) -> Case:
    view = read_customer_case(PostgresProcesses(conn), PostgresThreads(conn), customer_id, process_id)
    if view is None:
        raise not_found()
    return wire_case(view)


def wire_summary(case: CaseRow) -> CaseSummary:
    return CaseSummary(
        process_id=case.process_id,
        product=case.product,
        state=case.state,
        end_reason=case.end_reason,
        locale=case.locale,
    )


def wire_case(view: CaseView) -> Case:
    case = view.case
    return Case(
        process_id=case.process_id,
        state=case.state,
        end_reason=case.end_reason,
        product=case.product,
        locale=case.locale,
        messages=wire_thread(view.thread),
        certificate=None if view.certificate is None else wire_certificate(view.certificate),
        appealable=view.appealable,
    )


def wire_certificate(certificate: CertificateView) -> Certificate:
    income = certificate.income
    return Certificate(
        event_id=certificate.event_id,
        decided_by=certificate.decided_by,
        locale=certificate.locale,
        outcome=certificate.outcome,
        body=certificate.body,
        product=certificate.product,
        income_local=wire_optional_number(income.income_local),
        income_currency=income.income_currency,
        income_usd=wire_optional_number(income.income_usd),
        as_of=income.as_of,
    )
