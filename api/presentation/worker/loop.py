import logging
import threading
import time
from uuid import UUID

import psycopg
from psycopg_pool import ConnectionPool

from api.application.cycle.attempt import AttemptResult, run_claimed
from api.application.cycle.context import Cycle
from api.application.cycle.plan import PlanningEvents
from api.application.cycle.ports import ReadTurn
from api.infrastructure.db.commands import PostgresCommands
from api.infrastructure.db.events import PostgresEventLog, PostgresEvents
from api.infrastructure.db.messages import PostgresThread
from api.infrastructure.db.processes import PostgresProcesses
from api.infrastructure.db.profile import PostgresProfiles
from api.infrastructure.llm.conversation import CLAUDE_SONNET_5_5, ClaudeAccess, RecordCall, claude_turn_reader
from api.infrastructure.llm.keywords import B0_MODEL, read_keyword_turn

POLL_SECONDS = 1.0

logger = logging.getLogger(__name__)


# LLM_MODEL names what reads a turn: B0, the keyword baseline, or Claude Sonnet 5.5 (PLAN.md D23, D27).
def read_turn_for(model: str, access: ClaudeAccess, record: RecordCall) -> ReadTurn:
    if model == B0_MODEL:
        return read_keyword_turn
    if model == CLAUDE_SONNET_5_5:
        return claude_turn_reader(access, model, record)
    raise ValueError(f"LLM_MODEL={model} names nothing that reads a turn: use {CLAUDE_SONNET_5_5} or {B0_MODEL}")


def postgres_cycle(conn: psycopg.Connection, read_turn: ReadTurn) -> Cycle:
    log = PostgresEventLog(conn)
    queue = PostgresCommands(conn)
    processes = PostgresProcesses(conn)
    return Cycle(
        events=PlanningEvents(PostgresEvents(conn), log, queue),
        processes=processes,
        case=processes,
        log=log,
        queue=queue,
        profiles=PostgresProfiles(conn),
        thread=PostgresThread(conn),
        read_turn=read_turn,
    )


def run_next(pool: ConnectionPool, read_turn: ReadTurn, timeout_seconds: float = POLL_SECONDS) -> AttemptResult | None:
    with pool.connection(timeout=timeout_seconds) as conn, conn.transaction():
        cycle = postgres_cycle(conn, read_turn)
        claimed = cycle.queue.claim_next()
        if claimed is None:
            return None
        return run_claimed(cycle, claimed, conn.transaction)


def run_until_idle(pool: ConnectionPool, read_turn: ReadTurn) -> list[AttemptResult]:
    results: list[AttemptResult] = []
    while (result := run_next(pool, read_turn)) is not None:
        results.append(result)
    return results


def cycle_settled(pool: ConnectionPool, root_event_id: UUID) -> bool:
    with pool.connection() as conn:
        return PostgresCommands(conn).cycle_settled(root_event_id)


class Worker:
    def __init__(self, pool: ConnectionPool, read_turn: ReadTurn, poll_seconds: float = POLL_SECONDS) -> None:
        self._pool = pool
        self._read_turn = read_turn
        self._poll_seconds = poll_seconds
        self._wake = threading.Event()
        self._stopping = threading.Event()
        self._progress = threading.Condition()
        self._thread = threading.Thread(target=self._loop, name="alba-worker", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stopping.set()
        self._wake.set()
        self._thread.join()

    def wake(self) -> None:
        self._wake.set()

    def wait_for_cycle(self, root_event_id: UUID, timeout_seconds: float) -> bool:
        deadline = time.monotonic() + timeout_seconds
        while not cycle_settled(self._pool, root_event_id):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            with self._progress:
                self._progress.wait(min(remaining, self._poll_seconds))
        return True

    def _loop(self) -> None:
        while not self._stopping.is_set():
            if not self._step():
                self._wake.wait(self._poll_seconds)
                self._wake.clear()

    def _step(self) -> bool:
        try:
            result = run_next(self._pool, self._read_turn, self._poll_seconds)
        # A lost connection must not end the loop: nothing was decided, the command stays pending, and the next poll
        # takes it again.
        except Exception:
            logger.exception("the worker could not take a command")
            return False
        with self._progress:
            self._progress.notify_all()
        return result is not None
