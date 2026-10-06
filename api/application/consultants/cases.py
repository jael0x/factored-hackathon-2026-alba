from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from api.application.processes import Events
from api.contract_models import Actor, CloseOutcome, EventName, ProcessState
from api.domain.process.case import CaseRow
from api.domain.process.lifecycle import ENDED, HUMAN_ACTIVE, ProcessRow
from api.domain.process.new_events import AlreadyAppended, IdempotencyConflict, consultant_closed
from api.domain.process.packet import HandoffPacket, HandoffSource, QueueItem, packet_of
from api.domain.process.stored_events import Payload


@dataclass(frozen=True)
class TraceRecord:
    event_id: UUID
    event_name: EventName
    created_at: datetime
    actor: Actor
    process_id: UUID | None
    process_state: ProcessState
    caused_by_event_id: UUID | None
    payload: Payload


class ConsultantCases(Protocol):
    def queue(self) -> list[QueueItem]: ...

    def handoff(self, process_id: UUID) -> HandoffSource | None: ...

    def lock_handoff(self, process_id: UUID) -> HandoffSource | None: ...

    def trace(self, process_id: UUID) -> list[TraceRecord] | None: ...

    def case(self, process_id: UUID) -> CaseRow | None: ...


class ConsultantCaseNotFound(Exception):
    def __init__(self, process_id: UUID) -> None:
        super().__init__(f"process {process_id} is not with a person")


class CaseAlreadyClosed(Exception):
    def __init__(self, process_id: UUID) -> None:
        super().__init__(f"process {process_id} was already ended or closed")


class CaseNotClosable(Exception):
    def __init__(self, process_id: UUID) -> None:
        super().__init__(f"the policy reached no result on process {process_id}")


def list_consultant_queue(cases: ConsultantCases) -> list[QueueItem]:
    return cases.queue()


def read_handoff_packet(cases: ConsultantCases, process_id: UUID) -> HandoffPacket | None:
    source = cases.handoff(process_id)
    if source is None or source.state != HUMAN_ACTIVE:
        return None
    return packet_of(source)


def read_case_trace(cases: ConsultantCases, process_id: UUID) -> list[TraceRecord] | None:
    return cases.trace(process_id)


# The close only appends the consultant's event; close_on_consultant_decision and the worker render and end the case.
def close_consultant_case(
    events: Events, cases: ConsultantCases, consultant_id: str, process_id: UUID, outcome: CloseOutcome
) -> UUID:
    source = cases.lock_handoff(process_id)
    if source is not None and source.state == ENDED:
        raise CaseAlreadyClosed(process_id)
    if source is None or source.state != HUMAN_ACTIVE:
        raise ConsultantCaseNotFound(process_id)
    if not packet_of(source).closable:
        raise CaseNotClosable(process_id)
    process = ProcessRow(process_id=process_id, customer_id=source.customer_id, state=source.state)
    try:
        appended = events.append(consultant_closed(process, outcome, consultant_id, source.locale))
    except IdempotencyConflict:
        raise CaseAlreadyClosed(process_id) from None
    if isinstance(appended, AlreadyAppended):
        raise CaseAlreadyClosed(process_id)
    return appended.event_id


def read_consultant_case(cases: ConsultantCases, process_id: UUID) -> CaseRow | None:
    return cases.case(process_id)
