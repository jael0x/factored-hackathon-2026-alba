from dataclasses import dataclass
from uuid import UUID

from api.contract_models import (
    Actor,
    CloseOutcome,
    DecidedBy,
    EndReason,
    EventName,
    Locale,
    PolicyVersion,
    ProcessState,
    ProductKey,
    ReasonCode,
    TemplateId,
)
from api.domain.json_value import Payload
from api.domain.policy.engine import Decision, PolicyFact, TraceStep
from api.domain.process.events import (
    ANALYSIS_COMPLETED,
    CONSULTANT_CLOSED,
    EVENT_ACTOR,
    MESSAGE_RECEIVED,
    PREQUALIFICATION_DECIDED,
    PROCESS_ENDED,
    PROCESS_STARTED,
    PROCESS_STATE_CHANGED,
    TEMPLATE_SENT,
    THREAD_TAKEN,
    TURN_CLASSIFIED,
    ActionKey,
    consultant_close_key,
    decision_key,
    event_key,
    message_key,
    open_process_key,
    policy_key,
    template_key,
    turn_key,
)
from api.domain.process.lifecycle import (
    AI_ACTIVE,
    CREDIT_PREQUALIFICATION,
    ENDED,
    HUMAN_ACTIVE,
    MessageStamp,
    ProcessRow,
)
from api.domain.process.turns import ModelReading, TurnStamp, WithheldReading


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
    payload: Payload

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


def turn_classified(
    process: ProcessRow, locale: Locale, model: ModelReading, stamp: TurnStamp, cause: Cause
) -> NewEvent:
    reading = model.reading
    reason_code = model.reason_code if isinstance(model, WithheldReading) else None
    payload: Payload = {
        "intent": reading.intent,
        "product": stamp.product,
        "language": reading.language,
        "locale": locale,
        "declared_income_amount": reading.declared_income_amount,
        "declared_income_currency": reading.declared_income_currency,
        "reply_text": reading.reply_text,
        "reply_ok": reason_code is None,
        "reason_code": reason_code,
        "product_asked_count": stamp.product_asked_count,
        "income_requested": stamp.income_requested,
    }
    return _process_event(TURN_CLASSIFIED, turn_key(cause.event_id), process, process.state, cause, payload)


def template_sent(process: ProcessRow, locale: Locale, template_id: TemplateId, body: str, cause: Cause) -> NewEvent:
    key = template_key(template_id, cause.event_id)
    payload: Payload = {"locale": locale, "template_id": template_id, "body": body}
    return _process_event(TEMPLATE_SENT, key, process, process.state, cause, payload)


def analysis_completed(
    process: ProcessRow, decision: Decision, product: ProductKey, locale: Locale, cause: Cause
) -> NewEvent:
    key = policy_key(process.process_id, decision.policy_version, product, cause.event_id)
    payload: Payload = {
        "policy_version": decision.policy_version,
        "product": product,
        "outcome": decision.outcome,
        "deciding_rule": decision.deciding_rule,
        "rule_trace": [trace_step(step) for step in decision.rule_trace],
        "facts": [policy_fact(fact) for fact in decision.facts],
        "locale": locale,
    }
    return _process_event(ANALYSIS_COMPLETED, key, process, process.state, cause, payload)


def prequalification_decided(
    process: ProcessRow, locale: Locale, outcome: CloseOutcome, body: str, decided_by: DecidedBy, cause: Cause
) -> NewEvent:
    payload: Payload = {"locale": locale, "outcome": outcome, "body": body, "decided_by": decided_by}
    key = decision_key(process.process_id)
    return _process_event(PREQUALIFICATION_DECIDED, key, process, process.state, cause, payload)


def consultant_closed(process: ProcessRow, outcome: CloseOutcome, consultant_id: str, locale: Locale) -> NewEvent:
    return NewEvent(
        event_name=CONSULTANT_CLOSED,
        idempotency_key=consultant_close_key(process.process_id),
        customer_id=process.customer_id,
        process_id=process.process_id,
        process_state=process.state,
        caused_by_event_id=None,
        caused_by_command_id=None,
        payload={"outcome": outcome, "consultant_id": consultant_id, "locale": locale},
    )


def trace_step(step: TraceStep) -> Payload:
    return {"rule_id": step.rule_id, "input": dict(step.input), "result": step.result}


def policy_fact(fact: PolicyFact) -> Payload:
    return {"name": fact.name, "value": fact.value, "source": fact.source, "as_of": fact.as_of.isoformat()}


def _process_event(
    event_name: EventName,
    idempotency_key: str,
    process: ProcessRow,
    process_state: ProcessState,
    cause: Cause,
    payload: Payload,
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
