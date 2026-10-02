from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from api.domain.process.new_events import AlreadyAppended, Appended, AppendResult, IdempotencyConflict, NewEvent


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
