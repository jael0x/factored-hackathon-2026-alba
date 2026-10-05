from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import get_args
from uuid import UUID

from api.contract_models import EndReason, ProcessKey, ProcessState, ReasonCode
from api.domain.closed_sets import parse_member

AI_ACTIVE: ProcessState = "ai_active"
HUMAN_ACTIVE: ProcessState = "human_active"
ENDED: ProcessState = "ended"
PROCESS_STATES: frozenset[ProcessState] = frozenset(get_args(ProcessState))

PREQUALIFIED_END: EndReason = "prequalified"
NOT_PREQUALIFIED_END: EndReason = "not_prequalified"
END_REASONS: frozenset[EndReason] = frozenset(get_args(EndReason))

CUSTOMER_REQUESTED_HUMAN: ReasonCode = "customer_requested_human"
OUT_OF_SCOPE: ReasonCode = "out_of_scope"
LANGUAGE_UNSUPPORTED: ReasonCode = "language_unsupported"
MODEL_OUTPUT_INVALID: ReasonCode = "model_output_invalid"
TOOL_FAILED: ReasonCode = "tool_failed"
POLICY_REFER: ReasonCode = "policy_refer"
REPLY_FORBIDDEN: ReasonCode = "reply_forbidden"
REASON_CODES: frozenset[ReasonCode] = frozenset(get_args(ReasonCode))

CREDIT_PREQUALIFICATION: ProcessKey = "credit_prequalification"

MOVE_NEEDS_END_REASON: Mapping[tuple[ProcessState, ProcessState], bool] = MappingProxyType(
    {
        (AI_ACTIVE, HUMAN_ACTIVE): False,
        (AI_ACTIVE, ENDED): True,
        (HUMAN_ACTIVE, ENDED): True,
    }
)
REOPEN_MOVE: tuple[ProcessState, ProcessState] = (ENDED, HUMAN_ACTIVE)


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


# Reopening is not in the move table: only an appeal may make it (D25), so a handoff can never reopen a case.
def check_reopen(from_state: ProcessState) -> None:
    if (from_state, HUMAN_ACTIVE) != REOPEN_MOVE:
        raise IllegalTransition(from_state, HUMAN_ACTIVE, None)


def stamp_message(open_process: ProcessRow | None) -> MessageStamp:
    if open_process is None:
        return MessageStamp(process_id=None, process_state=AI_ACTIVE)
    return MessageStamp(process_id=open_process.process_id, process_state=open_process.state)
