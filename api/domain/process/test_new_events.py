from uuid import UUID

from api.domain.process.events import end_key, transition_key
from api.domain.process.lifecycle import MessageStamp, ProcessRow
from api.domain.process.new_events import (
    Cause,
    NewEvent,
    message_received,
    process_ended,
    process_started,
    state_changed,
    thread_taken,
)

PROCESS_ID = UUID("11111111-1111-4111-8111-111111111111")
EVENT_ID = UUID("22222222-2222-4222-8222-222222222222")
CLIENT_MESSAGE_ID = UUID("33333333-3333-4333-8333-333333333333")
COMMAND_ID = UUID("44444444-4444-4444-8444-444444444444")
JUAN = "CLI-9EDEKZ8OUNUR"
CAUSE = Cause(event_id=EVENT_ID, command_id=COMMAND_ID)
OPEN_CASE = ProcessRow(process_id=PROCESS_ID, customer_id=JUAN, state="ai_active")
HANDED_OFF = ProcessRow(process_id=PROCESS_ID, customer_id=JUAN, state="human_active")


def test_a_first_message_has_no_process_and_is_the_customers() -> None:
    event = message_received(JUAN, "quiero una tarjeta", CLIENT_MESSAGE_ID, "es", MessageStamp(None, "ai_active"))
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
        },
    )
    assert event.actor == "customer"


def test_a_message_to_a_handed_off_case_carries_that_state() -> None:
    event = message_received(JUAN, "hola", CLIENT_MESSAGE_ID, "es", MessageStamp(PROCESS_ID, "human_active"))
    assert (event.process_id, event.process_state) == (PROCESS_ID, "human_active")


def test_a_message_carries_the_language_chosen_with_the_switch() -> None:
    event = message_received(JUAN, "quiero una tarjeta", CLIENT_MESSAGE_ID, "en", MessageStamp(None, "ai_active"))
    assert event.payload["locale"] == "en"


def test_process_started_is_born_ai_active_and_points_at_its_message() -> None:
    event = process_started(OPEN_CASE, "pt", CAUSE)
    assert event == NewEvent(
        event_name="process.started",
        idempotency_key=f"process:{JUAN}:credit_prequalification:{EVENT_ID}",
        customer_id=JUAN,
        process_id=PROCESS_ID,
        process_state="ai_active",
        caused_by_event_id=EVENT_ID,
        caused_by_command_id=COMMAND_ID,
        payload={"process_key": "credit_prequalification", "customer_id": JUAN, "locale": "pt"},
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
    action = end_key(PROCESS_ID)
    changed = state_changed(HANDED_OFF, "ended", "not_prequalified", action, Cause(EVENT_ID, None))
    ended = process_ended(HANDED_OFF, "not_prequalified", None, action, Cause(EVENT_ID, None))
    assert changed == NewEvent(
        event_name="process.state_changed",
        idempotency_key=f"end:{PROCESS_ID}:process.state_changed",
        customer_id=JUAN,
        process_id=PROCESS_ID,
        process_state="ended",
        caused_by_event_id=EVENT_ID,
        caused_by_command_id=None,
        payload={"from_state": "human_active", "to_state": "ended", "end_reason": "not_prequalified"},
    )
    assert ended == NewEvent(
        event_name="process.ended",
        idempotency_key=f"end:{PROCESS_ID}:process.ended",
        customer_id=JUAN,
        process_id=PROCESS_ID,
        process_state="ended",
        caused_by_event_id=EVENT_ID,
        caused_by_command_id=None,
        payload={"end_reason": "not_prequalified", "policy_version": None},
    )
