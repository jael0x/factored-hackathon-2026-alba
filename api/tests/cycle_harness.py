import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, LiteralString
from uuid import UUID, uuid4

import psycopg
from psycopg_pool import ConnectionPool

from api.application.cycle.plan import PlanningEvents
from api.application.cycle.ports import TurnRequest
from api.application.processes import MessageTarget, record_customer_message
from api.contract_models import Locale
from api.domain.process.new_events import Appended, AppendResult, NewEvent
from api.domain.process.turns import ModelReading, ShownReading
from api.infrastructure.db.commands import PostgresCommands
from api.infrastructure.db.events import PostgresEventLog, PostgresEvents
from api.infrastructure.db.json_codec import configure_json
from api.infrastructure.db.pool import open_pool
from api.infrastructure.db.processes import PostgresProcesses
from api.infrastructure.llm.schema import reading_of
from api.tests.oracle import ORACLE, seed_oracle_profiles
from api.tests.turn_harness import TurnFixtureName, load_turn_fixture

JUAN = "CLI-9EDEKZ8OUNUR"
JULIANA = "CLI-MD60UR8PNJDI"
ALICIA = "CLI-440CO5FZIY6A"
MARIANA = "CLI-ZGOY1V6ZC46J"
NO_PROFILE = "CLI-NOPROFILE001"


class ModelDown(Exception):
    pass


@dataclass
class ScriptedModel:
    readings: Mapping[str, ModelReading]
    failures_left: int = 0
    calls: list[TurnRequest] = field(default_factory=list)

    def __call__(self, request: TurnRequest) -> ModelReading:
        self.calls.append(request)
        if self.failures_left > 0:
            self.failures_left -= 1
            raise ModelDown("the model did not answer")
        return self.readings[request.text]


def scripted(*names: TurnFixtureName, failures: int = 0) -> ScriptedModel:
    fixtures = [load_turn_fixture(name) for name in names]
    return ScriptedModel({f.text: ShownReading(reading_of(f.turn)) for f in fixtures}, failures)


def seed_cycle_people(url: str) -> None:
    with psycopg.connect(url) as conn:
        conn.cursor().executemany(
            """
            INSERT INTO customers (customer_id, document_number, first_name, last_name, country, segment, customer_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            [
                (c.customer_id, c.customer_id, c.first_name, c.last_name, c.country, c.segment, c.customer_status)
                for c in ORACLE.customers
            ]
            + [(NO_PROFILE, NO_PROFILE, "Nombre", "Apellido", "México", "Basic", "Active")],
        )
        seed_oracle_profiles(conn)


@contextmanager
def cycle_pool(url: str) -> Iterator[ConnectionPool]:
    pool = open_pool(url, 1, 4)
    pool.wait()
    try:
        yield pool
    finally:
        pool.close()


def planning(conn: psycopg.Connection) -> PlanningEvents:
    return PlanningEvents(PostgresEvents(conn), PostgresEventLog(conn), PostgresCommands(conn))


def send(
    pool: ConnectionPool,
    customer_id: str,
    text: str,
    target: MessageTarget,
    locale: Locale = "es",
    message_id: UUID | None = None,
) -> UUID:
    with pool.connection() as conn:
        result = record_customer_message(
            planning(conn), PostgresProcesses(conn), customer_id, text, message_id or uuid4(), locale, target
        )
    assert isinstance(result, Appended)
    return result.event_id


def append(pool: ConnectionPool, event: NewEvent) -> AppendResult:
    with pool.connection() as conn:
        return planning(conn).append(event)


def query(url: str, sql: LiteralString, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
    with psycopg.connect(url) as conn:
        configure_json(conn)
        return conn.execute(sql, params).fetchall()


def wait_until_blocked(url: str, backend_pid: int) -> None:
    deadline = time.monotonic() + 5
    with psycopg.connect(url, autocommit=True) as watcher:
        while time.monotonic() < deadline:
            row = watcher.execute(
                "SELECT wait_event_type FROM pg_stat_activity WHERE pid = %s", (backend_pid,)
            ).fetchone()
            if row is not None and row[0] == "Lock":
                return
            time.sleep(0.01)
    raise AssertionError(f"backend {backend_pid} never waited on a lock")
