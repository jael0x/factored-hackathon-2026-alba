from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from api.application.cycle.ports import ClaimedCommand
from api.domain.process.commands import DONE, FAILED, PENDING, command_payload, parse_command
from api.domain.process.rules import PlannedCommand

# A command waits while an earlier command for the same customer is pending, so the commands of one event run in the
# order the rules planned them, and two workers never run one customer's commands side by side. A row another worker
# holds stays pending, so SKIP LOCKED cannot jump the queue.
CLAIM_NEXT = """
    SELECT c.id, c.command_name, c.payload, c.triggered_by_event_id, c.attempt_count
    FROM commands c
    JOIN events e ON e.id = c.triggered_by_event_id
    WHERE c.status = %(pending_status)s
      AND NOT EXISTS (
          SELECT 1
          FROM commands ahead
          JOIN events ahead_event ON ahead_event.id = ahead.triggered_by_event_id
          WHERE ahead.status = %(pending_status)s AND ahead_event.customer_id = e.customer_id AND ahead.seq < c.seq
      )
    ORDER BY c.seq
    LIMIT 1
    FOR UPDATE OF c SKIP LOCKED
"""

CYCLE_SETTLED = """
    WITH RECURSIVE chain (event_id) AS (
        SELECT %(root)s::uuid
        UNION
        SELECT written.id
        FROM chain
        JOIN commands c ON c.triggered_by_event_id = chain.event_id
        JOIN events written ON written.caused_by_command_id = c.id
    )
    SELECT NOT EXISTS (
        SELECT 1 FROM commands c JOIN chain ON c.triggered_by_event_id = chain.event_id WHERE c.status = %(pending_status)s
    )
"""


class PostgresCommands:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def enqueue(self, planned: PlannedCommand) -> None:
        self._conn.execute(
            """
            INSERT INTO commands (command_name, payload, triggered_by_event_id, emitted_by_rule_id, idempotency_key, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (idempotency_key) DO NOTHING
            """,
            (
                planned.command.command_name,
                Jsonb(dict(command_payload(planned.command.payload))),
                planned.triggered_by_event_id,
                planned.emitted_by_rule_id,
                planned.idempotency_key,
                PENDING,
            ),
        )

    def claim_next(self) -> ClaimedCommand | None:
        row = self._conn.execute(CLAIM_NEXT, {"pending_status": PENDING}).fetchone()
        if row is None:
            return None
        command_id, command_name, payload, triggered_by_event_id, attempt_count = row
        return ClaimedCommand(command_id, parse_command(command_name, payload), triggered_by_event_id, attempt_count)

    def mark_done(self, command_id: UUID, attempt_count: int) -> None:
        self._conn.execute(
            "UPDATE commands SET status = %s, attempt_count = %s WHERE id = %s", (DONE, attempt_count, command_id)
        )

    def record_failure(self, command_id: UUID, attempt_count: int, error: str, final: bool) -> None:
        self._conn.execute(
            "UPDATE commands SET status = %s, attempt_count = %s, last_error = %s WHERE id = %s",
            (FAILED if final else PENDING, attempt_count, error, command_id),
        )

    def fail_later_siblings(self, command_id: UUID) -> None:
        self._conn.execute(
            """
            UPDATE commands later
            SET status = %(failed_status)s, last_error = 'an earlier command of the same event failed: ' || failed.id
            FROM commands failed
            WHERE failed.id = %(command_id)s
              AND later.triggered_by_event_id = failed.triggered_by_event_id
              AND later.seq > failed.seq
              AND later.status = %(pending_status)s
            """,
            {"failed_status": FAILED, "pending_status": PENDING, "command_id": command_id},
        )

    def cycle_settled(self, root_event_id: UUID) -> bool:
        row = self._conn.execute(CYCLE_SETTLED, {"root": root_event_id, "pending_status": PENDING}).fetchone()
        return row is not None and row[0] is True

    def failed_for(self, triggered_by_event_id: UUID) -> bool:
        row = self._conn.execute(
            "SELECT EXISTS (SELECT 1 FROM commands WHERE triggered_by_event_id = %s AND status = %s)",
            (triggered_by_event_id, FAILED),
        ).fetchone()
        return row is not None and row[0] is True
