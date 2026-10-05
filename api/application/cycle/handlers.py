from collections.abc import Mapping
from types import MappingProxyType

from api.application.cycle.context import Cycle, Handler, Trigger, stored
from api.application.cycle.generate import classify_message
from api.application.cycle.moves import end_case, hand_off_case, open_case
from api.application.cycle.notices import send_template, show_reply
from api.application.cycle.policy_run import run_policy
from api.application.cycle.ports import ClaimedCommand
from api.application.cycle.render import render_decision
from api.domain.process.commands import (
    COMMAND_NAMES,
    CONVERSATION_GENERATE,
    CONVERSATION_SHOW_REPLY,
    DECISION_RENDER,
    POLICY_RUN,
    PROCESS_END,
    PROCESS_START,
    PROCESS_TRANSITION,
    TEMPLATE_SEND,
    CommandName,
)
from api.domain.process.new_events import Cause

HANDLERS: Mapping[CommandName, Handler] = MappingProxyType(
    {
        PROCESS_START: open_case,
        PROCESS_TRANSITION: hand_off_case,
        PROCESS_END: end_case,
        CONVERSATION_GENERATE: classify_message,
        CONVERSATION_SHOW_REPLY: show_reply,
        TEMPLATE_SEND: send_template,
        POLICY_RUN: run_policy,
        DECISION_RENDER: render_decision,
    }
)


def require_handlers(handlers: Mapping[CommandName, Handler]) -> None:
    if set(handlers) != COMMAND_NAMES:
        raise ValueError(f"every command needs one handler: {sorted(COMMAND_NAMES - set(handlers))}")


def handle(cycle: Cycle, claimed: ClaimedCommand) -> None:
    row = cycle.log.read(claimed.triggered_by_event_id)
    trigger = Trigger(row, stored(row), Cause(row.event_id, claimed.command_id))
    HANDLERS[claimed.command.command_name](cycle, trigger, claimed.command.payload)


require_handlers(HANDLERS)
