from typing import Annotated
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, Request
from psycopg_pool import ConnectionPool

from api.application.consultants.cases import (
    CaseAlreadyClosed,
    CaseNotClosable,
    ConsultantCaseNotFound,
    Handoff,
    close_consultant_case,
    list_consultant_queue,
    read_case_trace,
    read_consultant_case,
    read_handoff,
)
from api.contract_models import (
    CaseTrace,
    CloseCaseRequest,
    CloseOutcome,
    ConsultantCase,
    ConsultantCloseResult,
    ConsultantQueue,
    ConsultantQueueItem,
)
from api.domain.process.case import NO_INCOME_FACTS
from api.domain.process.lifecycle import ENDED, HUMAN_ACTIVE
from api.domain.process.packet import QueueItem
from api.domain.process.rules import END_REASON_BY_OUTCOME
from api.domain.session.tokens import SessionClaims
from api.infrastructure.db.cases import PostgresThreads
from api.infrastructure.db.consultant_cases import PostgresConsultantCases
from api.presentation.http.cycle import planning, require_settled
from api.presentation.http.dependencies import get_connection, require_consultant
from api.presentation.http.errors import already_closed, case_not_closable, not_found
from api.presentation.http.thread import wire_thread
from api.presentation.http.trace import wire_trace
from api.presentation.http.wire_numbers import wire_optional_number

router = APIRouter(prefix="/consultant")

CloseRefusal = ConsultantCaseNotFound | CaseAlreadyClosed | CaseNotClosable


@router.get("/queue", response_model=ConsultantQueue)
def read_queue(
    _: Annotated[SessionClaims, Depends(require_consultant)],
    conn: Annotated[psycopg.Connection, Depends(get_connection)],
) -> ConsultantQueue:
    return ConsultantQueue(
        cases=[wire_queue_item(item) for item in list_consultant_queue(PostgresConsultantCases(conn))]
    )


@router.get("/case/{process_id}", response_model=ConsultantCase)
def read_packet(
    process_id: UUID,
    _: Annotated[SessionClaims, Depends(require_consultant)],
    conn: Annotated[psycopg.Connection, Depends(get_connection)],
) -> ConsultantCase:
    handoff = read_handoff(PostgresConsultantCases(conn), PostgresThreads(conn), process_id)
    if handoff is None:
        raise not_found()
    return wire_packet(handoff)


@router.get("/case/{process_id}/trace", response_model=CaseTrace)
def read_trace(
    process_id: UUID,
    _: Annotated[SessionClaims, Depends(require_consultant)],
    conn: Annotated[psycopg.Connection, Depends(get_connection)],
) -> CaseTrace:
    records = read_case_trace(PostgresConsultantCases(conn), process_id)
    if records is None:
        raise not_found()
    return wire_trace(process_id, records)


# The write and the read each take a pooled connection; none is held while the worker runs the close's commands.
@router.post("/case/{process_id}/close", response_model=ConsultantCloseResult)
def close_case(
    process_id: UUID,
    body: CloseCaseRequest,
    request: Request,
    session: Annotated[SessionClaims, Depends(require_consultant)],
) -> ConsultantCloseResult:
    pool: ConnectionPool = request.app.state.pool
    with pool.connection() as conn:
        try:
            event_id = close_consultant_case(
                planning(conn), PostgresConsultantCases(conn), session.sub, process_id, body.outcome
            )
        except (ConsultantCaseNotFound, CaseAlreadyClosed, CaseNotClosable) as refused:
            conn.rollback()
            raise close_refusal(refused) from None
    require_settled(request, event_id)
    with pool.connection() as conn:
        return closed_result(PostgresConsultantCases(conn), process_id, body.outcome)


def close_refusal(refused: CloseRefusal) -> Exception:
    if isinstance(refused, CaseAlreadyClosed):
        return already_closed()
    if isinstance(refused, CaseNotClosable):
        return case_not_closable()
    return not_found()


# A settled close that did not end its case failed for good in the worker, so the response fails loud.
def closed_result(cases: PostgresConsultantCases, process_id: UUID, outcome: CloseOutcome) -> ConsultantCloseResult:
    case = read_consultant_case(cases, process_id)
    end_reason = END_REASON_BY_OUTCOME[outcome]
    if case is None or case.state != ENDED or case.end_reason != end_reason:
        raise LookupError(f"the close of process {process_id} settled but did not end it as {end_reason}")
    return ConsultantCloseResult.model_validate(
        {"process_id": process_id, "state": ENDED, "end_reason": end_reason, "outcome": outcome}
    )


def wire_queue_item(item: QueueItem) -> ConsultantQueueItem:
    return ConsultantQueueItem(
        process_id=item.process_id,
        customer_id=item.customer_id,
        first_name=item.first_name,
        last_name=item.last_name,
        product=item.product,
        reason_code=item.reason_code,
        locale=item.locale,
    )


# state is a one-value enum on the wire; model_validate checks it against the generated model.
def wire_packet(handoff: Handoff) -> ConsultantCase:
    packet = handoff.packet
    result = packet.result
    income = NO_INCOME_FACTS if result is None else result.income
    return ConsultantCase.model_validate(
        {
            "process_id": packet.process_id,
            "state": HUMAN_ACTIVE,
            "customer_id": packet.customer_id,
            "first_name": packet.first_name,
            "last_name": packet.last_name,
            "product": None if result is None else result.product,
            "credit_score": None if result is None else result.credit_score,
            "income_local": wire_optional_number(income.income_local),
            "income_currency": income.income_currency,
            "income_usd": wire_optional_number(income.income_usd),
            "deciding_rule": None if result is None else result.deciding_rule,
            "policy_version": None if result is None else result.policy_version,
            "outcome": None if result is None else result.outcome,
            "reason_code": packet.reason_code,
            "locale": packet.locale,
            "closable": packet.closable,
            "messages": wire_thread(handoff.thread),
        }
    )
