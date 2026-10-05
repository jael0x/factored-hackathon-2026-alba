from typing import Annotated
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Request

from api.application.cases import (
    CaseNotAppealable,
    CaseView,
    appeal_customer_case,
    list_customer_cases,
    read_customer_case,
)
from api.application.cycle.plan import PlanningEvents
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
    ThreadMessage,
)
from api.domain.process.case import CaseRow, CertificateView
from api.domain.process.new_events import IdempotencyConflict
from api.domain.session.tokens import SessionClaims
from api.infrastructure.db.cases import PostgresThreads
from api.infrastructure.db.commands import PostgresCommands
from api.infrastructure.db.events import PostgresEventLog, PostgresEvents
from api.infrastructure.db.processes import PostgresProcesses
from api.presentation.http.dependencies import get_connection, require_customer
from api.presentation.http.errors import (
    case_already_open,
    case_ended,
    case_not_appealable,
    invalid_body,
    message_id_reused,
    not_found,
)
from api.presentation.worker.loop import Worker

router = APIRouter()

CYCLE_WAIT_SECONDS = 30.0


@router.post("/messages", response_model=Case)
def send_message(
    body: SendMessageRequest,
    request: Request,
    session: Annotated[SessionClaims, Depends(require_customer)],
    conn: Annotated[psycopg.Connection, Depends(get_connection)],
) -> Case:
    target = message_target(body)
    processes, log = PostgresProcesses(conn), PostgresEventLog(conn)
    try:
        sent = record_customer_message(
            planning(conn), processes, session.sub, body.text, body.client_message_id, body.locale, target
        )
    except (IdempotencyConflict, CaseAlreadyOpen, CaseEnded, CaseNotFound) as refused:
        conn.rollback()
        raise refusal(refused) from None
    conn.commit()
    wait_for_cycle(request, sent.event_id)
    process_id = log.process_named_by(sent.event_id)
    if process_id is None:
        raise LookupError(f"message {sent.event_id} opened no case and joined none")
    return case_or_not_found(conn, processes, session.sub, process_id)


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
    conn: Annotated[psycopg.Connection, Depends(get_connection)],
) -> Case:
    processes = PostgresProcesses(conn)
    try:
        appealed = appeal_customer_case(
            planning(conn), processes, PostgresThreads(conn), session.sub, process_id, body.locale
        )
    except (CaseNotFound, CaseNotAppealable) as refused:
        conn.rollback()
        raise refusal(refused) from None
    conn.commit()
    if appealed is not None:
        wait_for_cycle(request, appealed.event_id)
    return case_or_not_found(conn, processes, session.sub, process_id)


@router.get("/case/{process_id}", response_model=Case)
def read_case(
    process_id: UUID,
    session: Annotated[SessionClaims, Depends(require_customer)],
    conn: Annotated[psycopg.Connection, Depends(get_connection)],
) -> Case:
    return case_or_not_found(conn, PostgresProcesses(conn), session.sub, process_id)


# Exactly one of product (a start from the home's dialog) and process_id (a message in that case), D24.
def message_target(body: SendMessageRequest) -> MessageTarget:
    if body.product is not None and body.process_id is None:
        return StartCase(body.product)
    if body.process_id is not None and body.product is None:
        return InCase(body.process_id)
    raise invalid_body()


def refusal(refused: Exception) -> Exception:
    if isinstance(refused, CaseAlreadyOpen):
        return case_already_open()
    if isinstance(refused, CaseEnded):
        return case_ended()
    if isinstance(refused, CaseNotFound):
        return not_found()
    if isinstance(refused, CaseNotAppealable):
        return case_not_appealable()
    return message_id_reused()


def planning(conn: psycopg.Connection) -> PlanningEvents:
    return PlanningEvents(PostgresEvents(conn), PostgresEventLog(conn), PostgresCommands(conn))


# The answer is the case after the worker finished this event's cycle. A cycle that runs past CYCLE_WAIT_SECONDS,
# or an API with no worker, answers with the case as it stands; the page reads it again with GET /case.
def wait_for_cycle(request: Request, event_id: UUID) -> None:
    worker: Worker | None = request.app.state.worker
    if worker is not None:
        worker.wake()
        worker.wait_for_cycle(event_id, CYCLE_WAIT_SECONDS)


def case_or_not_found(
    conn: psycopg.Connection, processes: PostgresProcesses, customer_id: str, process_id: UUID
) -> Case:
    view = read_customer_case(processes, PostgresThreads(conn), customer_id, process_id)
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
        messages=[
            ThreadMessage(id=line.line_id, author=line.author, body=line.body, event_id=line.event_id)
            for line in view.thread
        ],
        certificate=None if view.certificate is None else wire_certificate(view.certificate),
    )


def wire_certificate(certificate: CertificateView) -> Certificate:
    return Certificate(
        event_id=certificate.event_id,
        decided_by=certificate.decided_by,
        locale=certificate.locale,
        outcome=certificate.outcome,
        body=certificate.body,
        product=certificate.product,
        income_local=None if certificate.income_local is None else float(certificate.income_local),
        income_currency=certificate.income_currency,
        income_usd=None if certificate.income_usd is None else float(certificate.income_usd),
        as_of=certificate.as_of,
    )
