from datetime import date
from decimal import Decimal
from uuid import UUID

from api.domain.policy.engine import Decision, PolicyFact, TraceStep
from api.domain.process.events import end_key, transition_key
from api.domain.process.lifecycle import MessageStamp, ProcessRow
from api.domain.process.new_events import (
    Cause,
    NewEvent,
    analysis_completed,
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
from api.domain.process.turns import ShownReading, TurnReading, TurnStamp, WithheldReading

PROCESS_ID = UUID("11111111-1111-4111-8111-111111111111")
EVENT_ID = UUID("22222222-2222-4222-8222-222222222222")
CLIENT_MESSAGE_ID = UUID("33333333-3333-4333-8333-333333333333")
COMMAND_ID = UUID("44444444-4444-4444-8444-444444444444")
JUAN = "CLI-9EDEKZ8OUNUR"
CAUSE = Cause(event_id=EVENT_ID, command_id=COMMAND_ID)
OPEN_CASE = ProcessRow(process_id=PROCESS_ID, customer_id=JUAN, state="ai_active")
HANDED_OFF = ProcessRow(process_id=PROCESS_ID, customer_id=JUAN, state="human_active")


def test_a_first_message_has_no_process_and_is_the_customers() -> None:
    event = message_received(
        JUAN, "quiero una tarjeta", CLIENT_MESSAGE_ID, "es", "credit_card", MessageStamp(None, "ai_active")
    )
    assert event == NewEvent(
        event_name="conversation.message_received",
        idempotency_key="msg:33333333-3333-4333-8333-333333333333",
        customer_id=JUAN,
        process_id=None,
        process_state="ai_active",
        caused_by_event_id=None,
        caused_by_command_id=None,
        payload={
            "text": "quiero una tarjeta",
            "client_message_id": "33333333-3333-4333-8333-333333333333",
            "locale": "es",
            "product": "credit_card",
        },
    )
    assert event.actor == "customer"


def test_a_message_to_a_handed_off_case_carries_that_state() -> None:
    event = message_received(JUAN, "hola", CLIENT_MESSAGE_ID, "es", None, MessageStamp(PROCESS_ID, "human_active"))
    assert (event.process_id, event.process_state, event.payload["product"]) == (PROCESS_ID, "human_active", None)


def test_a_message_carries_the_language_chosen_with_the_switch() -> None:
    event = message_received(JUAN, "quiero una tarjeta", CLIENT_MESSAGE_ID, "pt", None, MessageStamp(None, "ai_active"))
    assert event.payload["locale"] == "pt"


def test_process_started_is_born_ai_active_and_points_at_its_message() -> None:
    event = process_started(OPEN_CASE, "pt", "personal_loan", CAUSE)
    assert event == NewEvent(
        event_name="process.started",
        idempotency_key=f"process:{JUAN}:credit_prequalification:{EVENT_ID}",
        customer_id=JUAN,
        process_id=PROCESS_ID,
        process_state="ai_active",
        caused_by_event_id=EVENT_ID,
        caused_by_command_id=COMMAND_ID,
        payload={
            "process_key": "credit_prequalification",
            "customer_id": JUAN,
            "locale": "pt",
            "product": "personal_loan",
        },
    )
    assert event.actor == "system"


def test_a_handoff_writes_state_changed_and_thread_taken_with_the_new_state() -> None:
    action = transition_key(PROCESS_ID, "human_active", EVENT_ID)
    changed = state_changed(OPEN_CASE, "human_active", None, action, CAUSE)
    taken = thread_taken(OPEN_CASE, "policy_refer", action, CAUSE)
    assert changed == NewEvent(
        event_name="process.state_changed",
        idempotency_key=f"{action}:process.state_changed",
        customer_id=JUAN,
        process_id=PROCESS_ID,
        process_state="human_active",
        caused_by_event_id=EVENT_ID,
        caused_by_command_id=COMMAND_ID,
        payload={"from_state": "ai_active", "to_state": "human_active", "end_reason": None},
    )
    assert taken == NewEvent(
        event_name="conversation.thread_taken",
        idempotency_key=f"{action}:conversation.thread_taken",
        customer_id=JUAN,
        process_id=PROCESS_ID,
        process_state="human_active",
        caused_by_event_id=EVENT_ID,
        caused_by_command_id=COMMAND_ID,
        payload={"reason_code": "policy_refer", "from_state": "ai_active", "to_state": "human_active"},
    )
    assert (changed.actor, taken.actor) == ("system", "system")


def test_an_end_writes_both_events_with_the_same_end_reason() -> None:
    action = end_key(PROCESS_ID, EVENT_ID)
    changed = state_changed(HANDED_OFF, "ended", "not_prequalified", action, Cause(EVENT_ID, None))
    ended = process_ended(HANDED_OFF, "not_prequalified", None, action, Cause(EVENT_ID, None))
    assert changed == NewEvent(
        event_name="process.state_changed",
        idempotency_key=f"end:{PROCESS_ID}:{EVENT_ID}:process.state_changed",
        customer_id=JUAN,
        process_id=PROCESS_ID,
        process_state="ended",
        caused_by_event_id=EVENT_ID,
        caused_by_command_id=None,
        payload={"from_state": "human_active", "to_state": "ended", "end_reason": "not_prequalified"},
    )
    assert ended == NewEvent(
        event_name="process.ended",
        idempotency_key=f"end:{PROCESS_ID}:{EVENT_ID}:process.ended",
        customer_id=JUAN,
        process_id=PROCESS_ID,
        process_state="ended",
        caused_by_event_id=EVENT_ID,
        caused_by_command_id=None,
        payload={"end_reason": "not_prequalified", "policy_version": None},
    )


READING = TurnReading(
    intent="confirm_prequalify",
    product=None,
    language="es",
    declared_income_amount=Decimal("45000.50"),
    declared_income_currency="MXN",
    reply_text="De acuerdo.",
)
STAMP = TurnStamp(product="credit_card", product_asked_count=1, income_requested=True)


def test_a_shown_turn_carries_the_reading_the_stamps_and_the_locale_of_its_message() -> None:
    assert turn_classified(OPEN_CASE, "pt", ShownReading(READING), STAMP, CAUSE) == NewEvent(
        event_name="conversation.turn_classified",
        idempotency_key=f"turn:{EVENT_ID}",
        customer_id=JUAN,
        process_id=PROCESS_ID,
        process_state="ai_active",
        caused_by_event_id=EVENT_ID,
        caused_by_command_id=COMMAND_ID,
        payload={
            "intent": "confirm_prequalify",
            "product": "credit_card",
            "language": "es",
            "locale": "pt",
            "declared_income_amount": Decimal("45000.50"),
            "declared_income_currency": "MXN",
            "reply_text": "De acuerdo.",
            "reply_ok": True,
            "reason_code": None,
            "product_asked_count": 1,
            "income_requested": True,
            "open_case_product": None,
        },
    )


def test_a_withheld_turn_is_not_ok_and_names_its_reason() -> None:
    event = turn_classified(OPEN_CASE, "es", WithheldReading(READING, "reply_forbidden"), STAMP, CAUSE)
    assert (event.payload["reply_ok"], event.payload["reason_code"]) == (False, "reply_forbidden")


def test_a_sent_template_is_keyed_by_its_template_and_the_event_that_asked_for_it() -> None:
    assert template_sent(OPEN_CASE, "es", "needs_income", "¿Cuánto ganas?", CAUSE) == NewEvent(
        event_name="conversation.template_sent",
        idempotency_key=f"template:needs_income:{EVENT_ID}",
        customer_id=JUAN,
        process_id=PROCESS_ID,
        process_state="ai_active",
        caused_by_event_id=EVENT_ID,
        caused_by_command_id=COMMAND_ID,
        payload={"locale": "es", "template_id": "needs_income", "body": "¿Cuánto ganas?"},
    )


def test_an_analysis_carries_the_decision_the_product_and_the_locale() -> None:
    decision = Decision(
        outcome="PREQUALIFIED",
        deciding_rule="R05",
        rule_trace=(TraceStep("R05", {"credit_score": 812}, "PREQUALIFIED"),),
        facts=(PolicyFact("credit_score", 812, "customer_credit_profile.credit_score", date(2026, 6, 17)),),
        policy_version="alba-credit-v1",
    )
    assert analysis_completed(OPEN_CASE, decision, "credit_card", "es", CAUSE) == NewEvent(
        event_name="analysis.completed",
        idempotency_key=f"policy:{PROCESS_ID}:alba-credit-v1:credit_card:{EVENT_ID}",
        customer_id=JUAN,
        process_id=PROCESS_ID,
        process_state="ai_active",
        caused_by_event_id=EVENT_ID,
        caused_by_command_id=COMMAND_ID,
        payload={
            "policy_version": "alba-credit-v1",
            "product": "credit_card",
            "outcome": "PREQUALIFIED",
            "deciding_rule": "R05",
            "rule_trace": [{"rule_id": "R05", "input": {"credit_score": 812}, "result": "PREQUALIFIED"}],
            "facts": [
                {
                    "name": "credit_score",
                    "value": 812,
                    "source": "customer_credit_profile.credit_score",
                    "as_of": "2026-06-17",
                }
            ],
            "locale": "es",
        },
    )


def test_a_certificate_is_keyed_once_per_decider_and_carries_who_decided() -> None:
    assert prequalification_decided(HANDED_OFF, "pt", "NOT_PREQUALIFIED", "Você não…", "consultant", CAUSE) == NewEvent(
        event_name="prequalification.decided",
        idempotency_key=f"decision:{PROCESS_ID}:consultant",
        customer_id=JUAN,
        process_id=PROCESS_ID,
        process_state="human_active",
        caused_by_event_id=EVENT_ID,
        caused_by_command_id=COMMAND_ID,
        payload={"locale": "pt", "outcome": "NOT_PREQUALIFIED", "body": "Você não…", "decided_by": "consultant"},
    )


def test_a_consultant_close_is_the_consultants_and_keyed_once_per_case() -> None:
    event = consultant_closed(HANDED_OFF, "PREQUALIFIED", "AGT-OJ9N4FGYV9", "es")
    assert event == NewEvent(
        event_name="conversation.consultant_closed",
        idempotency_key=f"consultant_close:{PROCESS_ID}",
        customer_id=JUAN,
        process_id=PROCESS_ID,
        process_state="human_active",
        caused_by_event_id=None,
        caused_by_command_id=None,
        payload={"outcome": "PREQUALIFIED", "consultant_id": "AGT-OJ9N4FGYV9", "locale": "es"},
    )
    assert event.actor == "consultant"
