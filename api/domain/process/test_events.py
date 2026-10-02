from typing import assert_type, get_args
from uuid import UUID

from api.contract_models import EventName
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
    end_key,
    event_key,
    message_key,
    open_process_key,
    policy_key,
    template_key,
    transition_key,
    turn_key,
)

PROCESS_ID = UUID("11111111-1111-4111-8111-111111111111")
EVENT_ID = UUID("22222222-2222-4222-8222-222222222222")
CLIENT_MESSAGE_ID = UUID("33333333-3333-4333-8333-333333333333")

NAMED_EVENTS = (
    MESSAGE_RECEIVED,
    TURN_CLASSIFIED,
    TEMPLATE_SENT,
    CONSULTANT_CLOSED,
    THREAD_TAKEN,
    ANALYSIS_COMPLETED,
    PREQUALIFICATION_DECIDED,
    PROCESS_STARTED,
    PROCESS_STATE_CHANGED,
    PROCESS_ENDED,
)


def test_every_event_name_has_one_constant() -> None:
    assert sorted(NAMED_EVENTS) == sorted(get_args(EventName))


def test_the_customer_writes_the_message_the_consultant_the_close_and_commands_the_rest() -> None:
    assert dict(EVENT_ACTOR) == {
        "conversation.message_received": "customer",
        "conversation.turn_classified": "system",
        "conversation.template_sent": "system",
        "conversation.consultant_closed": "consultant",
        "conversation.thread_taken": "system",
        "analysis.completed": "system",
        "prequalification.decided": "system",
        "process.started": "system",
        "process.state_changed": "system",
        "process.ended": "system",
    }


def test_action_keys_follow_the_contract_table() -> None:
    assert [
        message_key(CLIENT_MESSAGE_ID),
        turn_key(EVENT_ID),
        template_key("needs_income", EVENT_ID),
        open_process_key("CLI-9EDEKZ8OUNUR", "credit_prequalification", EVENT_ID),
        policy_key(PROCESS_ID, "alba-credit-v1", "credit_card"),
        transition_key(PROCESS_ID, "human_active", EVENT_ID),
        consultant_close_key(PROCESS_ID),
        end_key(PROCESS_ID),
    ] == [
        "msg:33333333-3333-4333-8333-333333333333",
        "turn:22222222-2222-4222-8222-222222222222",
        "template:needs_income:22222222-2222-4222-8222-222222222222",
        "process:CLI-9EDEKZ8OUNUR:credit_prequalification:22222222-2222-4222-8222-222222222222",
        "policy:11111111-1111-4111-8111-111111111111:alba-credit-v1:credit_card",
        "transition:11111111-1111-4111-8111-111111111111:human_active:22222222-2222-4222-8222-222222222222",
        "consultant_close:11111111-1111-4111-8111-111111111111",
        "end:11111111-1111-4111-8111-111111111111",
    ]


def test_each_event_of_a_two_event_action_gets_its_own_key() -> None:
    transition = transition_key(PROCESS_ID, "human_active", EVENT_ID)
    end = end_key(PROCESS_ID)
    assert_type(transition, ActionKey)
    assert_type(end, ActionKey)
    keys = [
        event_key(transition, PROCESS_STATE_CHANGED),
        event_key(transition, THREAD_TAKEN),
        event_key(end, PROCESS_STATE_CHANGED),
        event_key(end, PROCESS_ENDED),
    ]
    assert keys == [
        f"{transition}:process.state_changed",
        f"{transition}:conversation.thread_taken",
        "end:11111111-1111-4111-8111-111111111111:process.state_changed",
        "end:11111111-1111-4111-8111-111111111111:process.ended",
    ]
    assert len(set(keys)) == len(keys)


def test_a_repeated_fact_repeats_its_key() -> None:
    assert message_key(CLIENT_MESSAGE_ID) == message_key(UUID(str(CLIENT_MESSAGE_ID)))
    assert transition_key(PROCESS_ID, "human_active", EVENT_ID) == transition_key(
        UUID(str(PROCESS_ID)), "human_active", UUID(str(EVENT_ID))
    )
