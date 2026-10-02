from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import get_args
from uuid import UUID

from api.contract_models import EndReason, ProcessKey, ProcessState
from api.domain.closed_sets import parse_member

AI_ACTIVE: ProcessState = "ai_active"
HUMAN_ACTIVE: ProcessState = "human_active"
ENDED: ProcessState = "ended"
PROCESS_STATES: frozenset[ProcessState] = frozenset(get_args(ProcessState))

CREDIT_PREQUALIFICATION: ProcessKey = "credit_prequalification"

MOVE_NEEDS_END_REASON: Mapping[tuple[ProcessState, ProcessState], bool] = MappingProxyType(
    {
        (AI_ACTIVE, HUMAN_ACTIVE): False,
        (AI_ACTIVE, ENDED): True,
        (HUMAN_ACTIVE, ENDED): True,
    }
)


class IllegalTransition(Exception):
    def __init__(self, from_state: ProcessState, to_state: ProcessState, end_reason: EndReason | None) -> None:
        super().__init__(f"process cannot move from {from_state} to {to_state} with end_reason {end_reason}")


@dataclass(frozen=True)
class ProcessRow:
    process_id: UUID
    customer_id: str
    state: ProcessState


@dataclass(frozen=True)
class MessageStamp:
    process_id: UUID | None
    process_state: ProcessState


def parse_state(value: object) -> ProcessState:
    return parse_member(value, PROCESS_STATES, "process state")


def check_move(from_state: ProcessState, to_state: ProcessState, end_reason: EndReason | None) -> None:
    needs_end_reason = MOVE_NEEDS_END_REASON.get((from_state, to_state))
    if needs_end_reason is None or needs_end_reason != (end_reason is not None):
        raise IllegalTransition(from_state, to_state, end_reason)


def stamp_message(open_process: ProcessRow | None) -> MessageStamp:
    if open_process is None:
        return MessageStamp(process_id=None, process_state=AI_ACTIVE)
    return MessageStamp(process_id=open_process.process_id, process_state=open_process.state)
