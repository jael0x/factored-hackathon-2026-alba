from collections.abc import Mapping
from types import MappingProxyType
from typing import NewType
from uuid import UUID

from api.contract_models import Actor, EventName, PolicyVersion, ProcessKey, ProcessState, ProductKey, TemplateId

MESSAGE_RECEIVED: EventName = "conversation.message_received"
TURN_CLASSIFIED: EventName = "conversation.turn_classified"
TEMPLATE_SENT: EventName = "conversation.template_sent"
CONSULTANT_CLOSED: EventName = "conversation.consultant_closed"
THREAD_TAKEN: EventName = "conversation.thread_taken"
ANALYSIS_COMPLETED: EventName = "analysis.completed"
PREQUALIFICATION_DECIDED: EventName = "prequalification.decided"
PROCESS_STARTED: EventName = "process.started"
PROCESS_STATE_CHANGED: EventName = "process.state_changed"
PROCESS_ENDED: EventName = "process.ended"

CUSTOMER_ACTOR: Actor = "customer"
CONSULTANT_ACTOR: Actor = "consultant"
SYSTEM_ACTOR: Actor = "system"

ActionKey = NewType("ActionKey", str)

EVENT_ACTOR: Mapping[EventName, Actor] = MappingProxyType(
    {
        MESSAGE_RECEIVED: CUSTOMER_ACTOR,
        TURN_CLASSIFIED: SYSTEM_ACTOR,
        TEMPLATE_SENT: SYSTEM_ACTOR,
        CONSULTANT_CLOSED: CONSULTANT_ACTOR,
        THREAD_TAKEN: SYSTEM_ACTOR,
        ANALYSIS_COMPLETED: SYSTEM_ACTOR,
        PREQUALIFICATION_DECIDED: SYSTEM_ACTOR,
        PROCESS_STARTED: SYSTEM_ACTOR,
        PROCESS_STATE_CHANGED: SYSTEM_ACTOR,
        PROCESS_ENDED: SYSTEM_ACTOR,
    }
)


def message_key(client_message_id: UUID) -> ActionKey:
    return ActionKey(f"msg:{client_message_id}")


def turn_key(triggered_by_event_id: UUID) -> ActionKey:
    return ActionKey(f"turn:{triggered_by_event_id}")


def template_key(template_id: TemplateId, triggered_by_event_id: UUID) -> ActionKey:
    return ActionKey(f"template:{template_id}:{triggered_by_event_id}")


def open_process_key(customer_id: str, process_key: ProcessKey, triggered_by_event_id: UUID) -> ActionKey:
    return ActionKey(f"process:{customer_id}:{process_key}:{triggered_by_event_id}")


def policy_key(
    process_id: UUID, policy_version: PolicyVersion, product: ProductKey, triggered_by_event_id: UUID
) -> ActionKey:
    return ActionKey(f"policy:{process_id}:{policy_version}:{product}:{triggered_by_event_id}")


def transition_key(process_id: UUID, to_state: ProcessState, caused_by_event_id: UUID) -> ActionKey:
    return ActionKey(f"transition:{process_id}:{to_state}:{caused_by_event_id}")


def consultant_close_key(process_id: UUID) -> ActionKey:
    return ActionKey(f"consultant_close:{process_id}")


def end_key(process_id: UUID) -> ActionKey:
    return ActionKey(f"end:{process_id}")


def event_key(action_key: ActionKey, event_name: EventName) -> str:
    return f"{action_key}:{event_name}"
