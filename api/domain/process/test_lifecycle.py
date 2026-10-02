import itertools
from typing import get_args
from uuid import UUID

import pytest

from api.contract_models import EndReason, ProcessState
from api.domain.process.lifecycle import (
    AI_ACTIVE,
    ENDED,
    HUMAN_ACTIVE,
    IllegalTransition,
    MessageStamp,
    ProcessRow,
    check_move,
    parse_state,
    stamp_message,
)

PROCESS_ID = UUID("11111111-1111-4111-8111-111111111111")
END_REASONS: tuple[EndReason | None, ...] = (None, *get_args(EndReason))
LEGAL_MOVES: set[tuple[ProcessState, ProcessState, EndReason | None]] = {
    ("ai_active", "human_active", None),
    ("ai_active", "ended", "prequalified"),
    ("ai_active", "ended", "not_prequalified"),
    ("human_active", "ended", "prequalified"),
    ("human_active", "ended", "not_prequalified"),
}
EVERY_MOVE = list(itertools.product(get_args(ProcessState), get_args(ProcessState), END_REASONS))


@pytest.mark.parametrize("move", sorted(LEGAL_MOVES, key=str))
def test_the_contract_moves_are_allowed(move: tuple[ProcessState, ProcessState, EndReason | None]) -> None:
    check_move(*move)


@pytest.mark.parametrize("move", [move for move in EVERY_MOVE if move not in LEGAL_MOVES], ids=str)
def test_every_other_move_is_refused(move: tuple[ProcessState, ProcessState, EndReason | None]) -> None:
    with pytest.raises(IllegalTransition, match=f"from {move[0]} to {move[1]} with end_reason {move[2]}"):
        check_move(*move)


def test_the_table_covers_every_pair_once() -> None:
    assert len(EVERY_MOVE) == 27
    assert len(LEGAL_MOVES) == 5


def test_a_message_with_no_open_case_has_no_process_and_the_birth_state() -> None:
    assert stamp_message(None) == MessageStamp(process_id=None, process_state=AI_ACTIVE)


@pytest.mark.parametrize("state", [AI_ACTIVE, HUMAN_ACTIVE])
def test_a_message_carries_the_open_case_and_its_state(state: ProcessState) -> None:
    open_case = ProcessRow(process_id=PROCESS_ID, customer_id="CLI-9EDEKZ8OUNUR", state=state)
    assert stamp_message(open_case) == MessageStamp(process_id=PROCESS_ID, process_state=state)


@pytest.mark.parametrize("value", ["ai_active", "human_active", "ended"])
def test_a_stored_state_is_read_back(value: str) -> None:
    assert parse_state(value) == value


def test_an_unknown_stored_state_fails_loud() -> None:
    with pytest.raises(ValueError, match="process state 'started' is not one of ai_active, ended, human_active"):
        parse_state("started")


def test_the_state_constants_are_the_wire_values() -> None:
    assert (AI_ACTIVE, HUMAN_ACTIVE, ENDED) == ("ai_active", "human_active", "ended")
