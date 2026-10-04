from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from api.contract_models import Actor, EndReason, EventName, Locale, PolicyVersion, ProcessState, ReasonCode
from api.domain.process.events import (
    EVENT_ACTOR,
    MESSAGE_RECEIVED,
    PROCESS_ENDED,
    PROCESS_STARTED,
    PROCESS_STATE_CHANGED,
    THREAD_TAKEN,
    ActionKey,
    event_key,
    message_key,
    open_process_key,
)
from api.domain.process.lifecycle import (
    AI_ACTIVE,
    CREDIT_PREQUALIFICATION,
    ENDED,
    HUMAN_ACTIVE,
    MessageStamp,
    ProcessRow,
)

PayloadValue = str | None


@dataclass(frozen=True)
class Cause:
    event_id: UUID
    command_id: UUID | None


@dataclass(frozen=True)
class NewEvent:
    event_name: EventName
    idempotency_key: str
    customer_id: str
    process_id: UUID | None
    process_state: ProcessState
    caused_by_event_id: UUID | None
    caused_by_command_id: UUID | None
    payload: Mapping[str, PayloadValue]

    @property
    def actor(self) -> Actor:
        return EVENT_ACTOR[self.event_name]


@dataclass(frozen=True)
class Appended:
    event_id: UUID


@dataclass(frozen=True)
class AlreadyAppended:
    event_id: UUID


AppendResult = Appended | AlreadyAppended


class IdempotencyConflict(Exception):
    def __init__(self, idempotency_key: str) -> None:
        super().__init__(f"idempotency key {idempotency_key} already names a different event")
        self.idempotency_key = idempotency_key


def message_received(
    customer_id: str, text: str, client_message_id: UUID, locale: Locale, stamp: MessageStamp
) -> NewEvent:
    return NewEvent(
        event_name=MESSAGE_RECEIVED,
        idempotency_key=message_key(client_message_id),
        customer_id=customer_id,
        process_id=stamp.process_id,
        process_state=stamp.process_state,
        caused_by_event_id=None,
        caused_by_command_id=None,
        payload={"text": text, "client_message_id": str(client_message_id), "locale": locale},
    )


def process_started(process: ProcessRow, locale: Locale, cause: Cause) -> NewEvent:
    key = open_process_key(process.customer_id, CREDIT_PREQUALIFICATION, cause.event_id)
    payload = {"process_key": CREDIT_PREQUALIFICATION, "customer_id": process.customer_id, "locale": locale}
    return _process_event(PROCESS_STARTED, key, process, AI_ACTIVE, cause, payload)


def state_changed(
    process: ProcessRow, to_state: ProcessState, end_reason: EndReason | None, action: ActionKey, cause: Cause
) -> NewEvent:
    key = event_key(action, PROCESS_STATE_CHANGED)
    payload = {"from_state": process.state, "to_state": to_state, "end_reason": end_reason}
    return _process_event(PROCESS_STATE_CHANGED, key, process, to_state, cause, payload)


def thread_taken(process: ProcessRow, reason_code: ReasonCode, action: ActionKey, cause: Cause) -> NewEvent:
    key = event_key(action, THREAD_TAKEN)
    payload = {"reason_code": reason_code, "from_state": process.state, "to_state": HUMAN_ACTIVE}
    return _process_event(THREAD_TAKEN, key, process, HUMAN_ACTIVE, cause, payload)


def process_ended(
    process: ProcessRow, end_reason: EndReason, policy_version: PolicyVersion | None, action: ActionKey, cause: Cause
) -> NewEvent:
    key = event_key(action, PROCESS_ENDED)
    payload = {"end_reason": end_reason, "policy_version": policy_version}
    return _process_event(PROCESS_ENDED, key, process, ENDED, cause, payload)


def _process_event(
    event_name: EventName,
    idempotency_key: str,
    process: ProcessRow,
    process_state: ProcessState,
    cause: Cause,
    payload: Mapping[str, PayloadValue],
) -> NewEvent:
    return NewEvent(
        event_name=event_name,
        idempotency_key=idempotency_key,
        customer_id=process.customer_id,
        process_id=process.process_id,
        process_state=process_state,
        caused_by_event_id=cause.event_id,
        caused_by_command_id=cause.command_id,
        payload=payload,
    )
