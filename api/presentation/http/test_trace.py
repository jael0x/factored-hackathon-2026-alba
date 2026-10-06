import json
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from api.application.consultants.cases import TraceRecord
from api.domain.policy.engine import CreditProfile, decide
from api.domain.process.events import end_key, transition_key
from api.domain.process.lifecycle import MessageStamp, ProcessRow
from api.domain.process.new_events import (
    Cause,
    NewEvent,
    analysis_completed,
    appeal_requested,
    consultant_closed,
    message_received,
    prequalification_decided,
    process_ended,
    process_started,
    state_changed,
    template_sent,
    thread_taken,
    turn_classified,
)
from api.domain.process.stored_events import EVENT_NAMES, Payload
from api.domain.process.turns import ShownReading, TurnReading, TurnStamp, WithheldReading
from api.presentation.http.trace import TRACE_MODELS, wire_trace, wire_trace_event
from api.presentation.http.wire_numbers import wire_json

PROCESS_ID = UUID("11111111-1111-4111-8111-111111111111")
EVENT_ID = UUID("22222222-2222-4222-8222-222222222222")
CLIENT_MESSAGE_ID = UUID("33333333-3333-4333-8333-333333333333")
ALICIA = "CLI-440CO5FZIY6A"
CESAR = "AGT-OJ9N4FGYV9"
CAUSE = Cause(event_id=EVENT_ID, command_id=None)
OPEN_CASE = ProcessRow(process_id=PROCESS_ID, customer_id=ALICIA, state="ai_active")
HANDED_OFF = ProcessRow(process_id=PROCESS_ID, customer_id=ALICIA, state="human_active")
WRITTEN_AT = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)
PROFILE = CreditProfile(
    customer_status="Active",
    credit_score=615,
    income_local=Decimal("4707334.28"),
    income_currency="COP",
    income_usd=Decimal("1167.42"),
    max_days_past_due=0,
    has_active_card=False,
    has_active_personal_loan=False,
    as_of=date(2026, 6, 17),
)
READING = TurnReading(
    intent="provide_income",
    product="credit_card",
    language="es",
    declared_income_amount=Decimal("4500000.50"),
    declared_income_currency="COP",
    reply_text="Gracias.",
)
STAMP = TurnStamp(product="credit_card", product_asked_count=0, income_requested=True)
MOVE = transition_key(PROCESS_ID, "human_active", EVENT_ID)
END = end_key(PROCESS_ID, EVENT_ID)

EVERY_EVENT: list[NewEvent] = [
    message_received(
        ALICIA, "Quiero una tarjeta", CLIENT_MESSAGE_ID, "es", "credit_card", MessageStamp(None, "ai_active")
    ),
    process_started(OPEN_CASE, "es", "credit_card", CAUSE),
    turn_classified(OPEN_CASE, "es", ShownReading(READING), STAMP, CAUSE),
    turn_classified(OPEN_CASE, "es", WithheldReading(READING, "reply_forbidden"), STAMP, CAUSE),
    analysis_completed(OPEN_CASE, decide(PROFILE, "credit_card", None), "credit_card", "es", CAUSE),
    template_sent(OPEN_CASE, "es", "refer_notice", "Una persona revisará tu solicitud.", CAUSE),
    state_changed(OPEN_CASE, "human_active", None, MOVE, CAUSE),
    thread_taken(OPEN_CASE, "policy_refer", MOVE, CAUSE),
    consultant_closed(HANDED_OFF, "PREQUALIFIED", CESAR, "es"),
    prequalification_decided(HANDED_OFF, "es", "PREQUALIFIED", "Precalificas.", "consultant", CAUSE),
    process_ended(HANDED_OFF, "prequalified", None, END, CAUSE),
    appeal_requested(ProcessRow(PROCESS_ID, ALICIA, "ended"), "es", "credit_card"),
]


def record(event: NewEvent, payload: Payload | None = None) -> TraceRecord:
    return TraceRecord(
        event_id=EVENT_ID,
        event_name=event.event_name,
        created_at=WRITTEN_AT,
        actor=event.actor,
        process_id=event.process_id,
        process_state=event.process_state,
        caused_by_event_id=event.caused_by_event_id,
        payload=event.payload if payload is None else payload,
    )


def test_every_event_name_has_one_trace_model() -> None:
    assert TRACE_MODELS.keys() == EVENT_NAMES


def test_every_event_name_is_built_below() -> None:
    assert {event.event_name for event in EVERY_EVENT} == EVENT_NAMES


@pytest.mark.parametrize("event", EVERY_EVENT, ids=lambda event: event.idempotency_key)
def test_every_event_a_builder_writes_is_its_trace_type_with_its_whole_payload(event: NewEvent) -> None:
    traced = wire_trace_event(record(event))
    assert type(traced) is TRACE_MODELS[event.event_name]
    assert traced.model_dump(mode="json") == {
        "id": str(EVENT_ID),
        "event_name": event.event_name,
        "created_at": "2026-10-05T12:00:00Z",
        "actor": event.actor,
        "process_id": None if event.process_id is None else str(event.process_id),
        "process_state": event.process_state,
        "caused_by_event_id": None if event.caused_by_event_id is None else str(event.caused_by_event_id),
        **json.loads(json.dumps(wire_json(event.payload))),
    }


def test_the_amounts_inside_the_trace_reach_the_wire_as_numbers() -> None:
    analysis = next(event for event in EVERY_EVENT if event.event_name == "analysis.completed")
    [written] = json.loads(wire_trace(PROCESS_ID, [record(analysis)]).model_dump_json())["events"]
    cited = [step["input"]["income_local"] for step in written["rule_trace"] if "income_local" in step["input"]]
    facts = {fact["name"]: fact["value"] for fact in written["facts"]}
    assert cited == [4707334.28]
    assert (facts["income_local"], facts["income_usd"], facts["credit_score"]) == (4707334.28, 1167.42, 615)


def test_a_payload_that_names_a_column_fails_loud() -> None:
    message = EVERY_EVENT[0]
    with pytest.raises(ValueError, match=f"event {EVENT_ID} has a payload the trace cannot carry"):
        wire_trace_event(record(message, {**message.payload, "process_state": "ended"}))


def test_a_payload_that_drifts_from_the_contract_names_the_event() -> None:
    message = EVERY_EVENT[0]
    with pytest.raises(ValueError, match=f"event {EVENT_ID} does not match TraceMessageReceived"):
        wire_trace_event(record(message, {**message.payload, "consultant_id": CESAR}))
