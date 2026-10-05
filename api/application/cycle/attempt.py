import logging
from dataclasses import dataclass

from api.application.cycle.context import Cycle
from api.application.cycle.handlers import handle
from api.application.cycle.ports import ClaimedCommand, EventRow, Savepoint
from api.application.processes import hand_off_process
from api.domain.process.commands import MAX_ATTEMPTS
from api.domain.process.lifecycle import AI_ACTIVE, CREDIT_PREQUALIFICATION, TOOL_FAILED, ProcessRow
from api.domain.process.new_events import Cause

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Done:
    attempts: int


@dataclass(frozen=True)
class Retried:
    attempts: int
    error: str


@dataclass(frozen=True)
class Failed:
    attempts: int
    error: str


AttemptResult = Done | Retried | Failed


def run_claimed(cycle: Cycle, claimed: ClaimedCommand, savepoint: Savepoint) -> AttemptResult:
    attempts = claimed.attempt_count + 1
    try:
        with savepoint():
            handle(cycle, claimed)
            cycle.queue.mark_done(claimed.command_id, attempts)
        return Done(attempts)
    # Any failure of a command is an attempt the queue must count; the command row records it and stops at three.
    except Exception as error:
        logger.exception("command %s failed on attempt %d", claimed.command_id, attempts)
        reason = f"{type(error).__name__}: {error}"
        final = attempts >= MAX_ATTEMPTS
        cycle.queue.record_failure(claimed.command_id, attempts, reason, final)
        if not final:
            return Retried(attempts, reason)
        cycle.queue.fail_later_siblings(claimed.command_id)
        hand_off_after_failure(cycle, claimed, savepoint)
        return Failed(attempts, reason)


def hand_off_after_failure(cycle: Cycle, claimed: ClaimedCommand, savepoint: Savepoint) -> None:
    row = cycle.log.read(claimed.triggered_by_event_id)
    process = case_behind(cycle, row)
    if process is None or process.state != AI_ACTIVE:
        state = None if process is None else process.state
        logger.error("command %s failed for good and its case (%s) cannot go to a person", claimed.command_id, state)
        return
    with savepoint():
        hand_off_process(
            cycle.events, cycle.processes, process.process_id, TOOL_FAILED, Cause(row.event_id, claimed.command_id)
        )


def case_behind(cycle: Cycle, row: EventRow) -> ProcessRow | None:
    if row.process_id is not None:
        return cycle.case.read(row.process_id)
    return cycle.processes.find_open(row.customer_id, CREDIT_PREQUALIFICATION)
