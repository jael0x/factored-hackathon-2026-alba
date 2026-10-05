from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from api.contract_models import EndReason, Locale, PolicyVersion, ProcessKey, ProcessState, ProductKey, ReasonCode
from api.domain.process.events import (
    PROCESS_STATE_CHANGED,
    end_key,
    event_key,
    message_key,
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
    def find_open(self, customer_id: str, process_key: ProcessKey, product: ProductKey) -> ProcessRow | None: ...

    def read_for_message(self, customer_id: str, process_id: UUID) -> ProcessRow | None: ...

    def insert_open(
        self, customer_id: str, process_key: ProcessKey, locale: Locale, product: ProductKey
    ) -> UUID | None: ...

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


class CaseNotFound(Exception):
    def __init__(self, process_id: UUID) -> None:
        super().__init__(f"process {process_id} is not this customer's")


class CaseEnded(Exception):
    def __init__(self, process_id: UUID) -> None:
        super().__init__(f"process {process_id} has ended")


class CaseAlreadyOpen(Exception):
    def __init__(self, product: ProductKey) -> None:
        super().__init__(f"the customer already has an open {product} case")


# A message starts a case for a product (the home's dialog, D24) or belongs to one of the customer's cases.
@dataclass(frozen=True)
class StartCase:
    product: ProductKey


@dataclass(frozen=True)
class InCase:
    process_id: UUID


MessageTarget = StartCase | InCase


def record_customer_message(
    events: Events,
    processes: Processes,
    customer_id: str,
    text: str,
    client_message_id: UUID,
    locale: Locale,
    target: MessageTarget,
) -> AppendResult:
    replay = events.has_key(message_key(client_message_id))
    if isinstance(target, StartCase):
        if not replay and processes.find_open(customer_id, CREDIT_PREQUALIFICATION, target.product) is not None:
            raise CaseAlreadyOpen(target.product)
        stamp = stamp_message(None)
        product: ProductKey | None = target.product
    else:
        stamp = stamp_message(case_for_message(processes, customer_id, target.process_id, replay))
        product = None
    return events.append(message_received(customer_id, text, client_message_id, locale, product, stamp))


def case_for_message(processes: Processes, customer_id: str, process_id: UUID, replay: bool) -> ProcessRow | None:
    process = processes.read_for_message(customer_id, process_id)
    if process is None:
        raise CaseNotFound(process_id)
    if process.state == ENDED:
        if replay:
            return None
        raise CaseEnded(process_id)
    return process


def start_process(
    events: Events, processes: Processes, customer_id: str, locale: Locale, product: ProductKey, cause: Cause
) -> StartResult:
    replayed = events.process_started_by(open_process_key(customer_id, CREDIT_PREQUALIFICATION, cause.event_id))
    if replayed is not None:
        return AlreadyStarted(replayed)
    process_id = processes.insert_open(customer_id, CREDIT_PREQUALIFICATION, locale, product)
    if process_id is None:
        return AlreadyOpen(read_open(processes, customer_id, product).process_id)
    events.append(process_started(ProcessRow(process_id, customer_id, AI_ACTIVE), locale, product, cause))
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
    action = end_key(process_id, cause.event_id)
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


def read_open(processes: Processes, customer_id: str, product: ProductKey) -> ProcessRow:
    open_case = processes.find_open(customer_id, CREDIT_PREQUALIFICATION, product)
    if open_case is None:
        raise OpenProcessVanished(customer_id)
    return open_case
