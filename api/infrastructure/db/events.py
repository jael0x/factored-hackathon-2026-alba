from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from api.application.cycle.ports import EventRow
from api.domain.process.new_events import AlreadyAppended, Appended, AppendResult, IdempotencyConflict, NewEvent

EVENT_COLUMNS = "id, event_name, customer_id, process_id, process_state, caused_by_event_id, seq, payload"


class PostgresEvents:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def append(self, event: NewEvent) -> AppendResult:
        payload = Jsonb(dict(event.payload))
        inserted = self._conn.execute(
            """
            INSERT INTO events (
                event_name, payload, customer_id, process_id, process_state, actor,
                caused_by_event_id, caused_by_command_id, idempotency_key
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (idempotency_key) DO NOTHING
            RETURNING id
            """,
            (
                event.event_name,
                payload,
                event.customer_id,
                event.process_id,
                event.process_state,
                event.actor,
                event.caused_by_event_id,
                event.caused_by_command_id,
                event.idempotency_key,
            ),
        ).fetchone()
        if inserted is not None:
            return Appended(inserted[0])
        [(event_id, same_fact)] = self._conn.execute(
            """
            SELECT id, event_name = %s AND customer_id = %s AND payload = %s
            FROM events
            WHERE idempotency_key = %s
            """,
            (event.event_name, event.customer_id, payload, event.idempotency_key),
        ).fetchall()
        if not same_fact:
            raise IdempotencyConflict(event.idempotency_key)
        return AlreadyAppended(event_id)

    def has_key(self, idempotency_key: str) -> bool:
        row = self._conn.execute("SELECT 1 FROM events WHERE idempotency_key = %s", (idempotency_key,)).fetchone()
        return row is not None

    def process_started_by(self, idempotency_key: str) -> UUID | None:
        row = self._conn.execute(
            "SELECT process_id FROM events WHERE idempotency_key = %s", (idempotency_key,)
        ).fetchone()
        return row[0] if row else None


class PostgresEventLog:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def read(self, event_id: UUID) -> EventRow:
        row = self._conn.execute(f"SELECT {EVENT_COLUMNS} FROM events WHERE id = %s", (event_id,)).fetchone()
        if row is None:
            raise LookupError(f"event {event_id} does not exist")
        return EventRow(*row)

    # A message names its case, or, for a start, the case its process.start opened (D24).
    def process_named_by(self, event_id: UUID) -> UUID | None:
        row = self._conn.execute(
            """
            SELECT process_id FROM events WHERE id = %s AND process_id IS NOT NULL
            UNION ALL
            (SELECT process_id FROM events WHERE caused_by_event_id = %s AND process_id IS NOT NULL ORDER BY seq LIMIT 1)
            LIMIT 1
            """,
            (event_id, event_id),
        ).fetchone()
        return row[0] if row else None

    def earlier(self, process_id: UUID, before_seq: int) -> list[EventRow]:
        rows = self._conn.execute(
            f"SELECT {EVENT_COLUMNS} FROM events WHERE process_id = %s AND seq < %s ORDER BY seq",
            (process_id, before_seq),
        ).fetchall()
        return [EventRow(*row) for row in rows]
