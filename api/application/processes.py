from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from api.contract_models import EndReason, Locale, PolicyVersion, ProcessKey, ProcessState, ReasonCode
from api.domain.process.events import (
    PROCESS_STATE_CHANGED,
    end_key,
    event_key,
    open_process_key,
    transition_key,
)
from api.domain.process.lifecycle import (
    AI_ACTIVE,
    CREDIT_PREQUALIFICATION,
    ENDED,
    HUMAN_ACTIVE,
    ProcessRow,
    check_move,
    stamp_message,
)
from api.domain.process.new_events import (
    AppendResult,
    Cause,
    NewEvent,
    message_received,
    process_ended,
    process_started,
    state_changed,
    thread_taken,
)


class Events(Protocol):
    def append(self, event: NewEvent) -> AppendResult: ...

    def has_key(self, idempotency_key: str) -> bool: ...

    def process_started_by(self, idempotency_key: str) -> UUID | None: ...


class Processes(Protocol):
    def find_open(self, customer_id: str, process_key: ProcessKey) -> ProcessRow | None: ...

    def insert_open(self, customer_id: str, process_key: ProcessKey, locale: Locale) -> UUID | None: ...

    def lock(self, process_id: UUID) -> ProcessRow | None: ...

    def set_state(self, process_id: UUID, state: ProcessState, end_reason: EndReason | None) -> None: ...


@dataclass(frozen=True)
class Started:
    process_id: UUID


@dataclass(frozen=True)
class AlreadyStarted:
    process_id: UUID


@dataclass(frozen=True)
class AlreadyOpen:
    process_id: UUID


StartResult = Started | AlreadyStarted | AlreadyOpen


@dataclass(frozen=True)
class Applied:
    process_id: UUID


@dataclass(frozen=True)
class AlreadyApplied:
    process_id: UUID


MoveResult = Applied | AlreadyApplied


class ProcessNotFound(Exception):
    def __init__(self, process_id: UUID) -> None:
        super().__init__(f"process {process_id} does not exist")


class OpenProcessVanished(Exception):
    def __init__(self, customer_id: str) -> None:
        super().__init__(f"the open process of {customer_id} blocked the insert and was gone when read")


def record_customer_message(
    events: Events, processes: Processes, customer_id: str, text: str, client_message_id: UUID, locale: Locale
) -> AppendResult:
    open_case = processes.find_open(customer_id, CREDIT_PREQUALIFICATION)
    return events.append(message_received(customer_id, text, client_message_id, locale, stamp_message(open_case)))


def start_process(events: Events, processes: Processes, customer_id: str, locale: Locale, cause: Cause) -> StartResult:
    replayed = events.process_started_by(open_process_key(customer_id, CREDIT_PREQUALIFICATION, cause.event_id))
    if replayed is not None:
        return AlreadyStarted(replayed)
    process_id = processes.insert_open(customer_id, CREDIT_PREQUALIFICATION, locale)
    if process_id is None:
        return AlreadyOpen(read_open(processes, customer_id).process_id)
    events.append(process_started(ProcessRow(process_id, customer_id, AI_ACTIVE), locale, cause))
    return Started(process_id)


def hand_off_process(
    events: Events, processes: Processes, process_id: UUID, reason_code: ReasonCode, cause: Cause
) -> MoveResult:
    process = lock(processes, process_id)
    action = transition_key(process_id, HUMAN_ACTIVE, cause.event_id)
    if events.has_key(event_key(action, PROCESS_STATE_CHANGED)):
        return AlreadyApplied(process_id)
    check_move(process.state, HUMAN_ACTIVE, None)
    processes.set_state(process_id, HUMAN_ACTIVE, None)
    events.append(state_changed(process, HUMAN_ACTIVE, None, action, cause))
    events.append(thread_taken(process, reason_code, action, cause))
    return Applied(process_id)


def end_process(
    events: Events,
    processes: Processes,
    process_id: UUID,
    end_reason: EndReason,
    policy_version: PolicyVersion | None,
    cause: Cause,
) -> MoveResult:
    process = lock(processes, process_id)
    action = end_key(process_id)
    if events.has_key(event_key(action, PROCESS_STATE_CHANGED)):
        return AlreadyApplied(process_id)
    check_move(process.state, ENDED, end_reason)
    processes.set_state(process_id, ENDED, end_reason)
    events.append(state_changed(process, ENDED, end_reason, action, cause))
    events.append(process_ended(process, end_reason, policy_version, action, cause))
    return Applied(process_id)


def lock(processes: Processes, process_id: UUID) -> ProcessRow:
    process = processes.lock(process_id)
    if process is None:
        raise ProcessNotFound(process_id)
    return process


def read_open(processes: Processes, customer_id: str) -> ProcessRow:
    open_case = processes.find_open(customer_id, CREDIT_PREQUALIFICATION)
    if open_case is None:
        raise OpenProcessVanished(customer_id)
    return open_case
