from datetime import datetime
from typing import LiteralString
from uuid import UUID

import psycopg
from psycopg import sql

from api.application.consultants.cases import TraceRecord
from api.domain.closed_sets import parse_member
from api.domain.locale import LOCALES
from api.domain.process.case import CaseRow
from api.domain.process.events import ACTORS, ANALYSIS_COMPLETED, MESSAGE_RECEIVED, THREAD_TAKEN
from api.domain.process.lifecycle import HUMAN_ACTIVE, parse_state
from api.domain.process.packet import HandoffSource, QueueItem, StoredEvent, handoff_reason
from api.domain.process.stored_events import EVENT_NAMES, Payload, parse_optional_product
from api.infrastructure.db.processes import case_row

# The partial index of 012 matches only the literal state, so the queue query carries it as one.
QUEUE = sql.SQL(
    """
    SELECT p.id, p.customer_id, c.first_name, c.last_name, p.product, p.locale, t.id, t.payload
    FROM processes p
    JOIN customers c ON c.customer_id = p.customer_id
    LEFT JOIN LATERAL (
        SELECT e.id, e.payload FROM events e
        WHERE e.process_id = p.id AND e.event_name = %(taken)s
        ORDER BY e.seq DESC
        LIMIT 1
    ) t ON true
    WHERE p.state = {human_active}
    ORDER BY p.created_at, p.id
    """
).format(human_active=sql.Literal(HUMAN_ACTIVE))

HANDOFF: LiteralString = """
    SELECT p.id, p.customer_id, c.first_name, c.last_name, p.state, p.locale, a.id, a.payload, t.id, t.payload
    FROM processes p
    JOIN customers c ON c.customer_id = p.customer_id
    LEFT JOIN LATERAL (
        SELECT e.id, e.payload FROM events e
        WHERE e.process_id = p.id AND e.event_name = %(analysis)s
        ORDER BY e.seq DESC
        LIMIT 1
    ) a ON true
    LEFT JOIN LATERAL (
        SELECT e.id, e.payload FROM events e
        WHERE e.process_id = p.id AND e.event_name = %(taken)s
        ORDER BY e.seq DESC
        LIMIT 1
    ) t ON true
    WHERE p.id = %(process)s
    """

TRACE: LiteralString = """
    SELECT e.id, e.event_name, e.created_at, e.actor, e.process_id, e.process_state, e.caused_by_event_id,
           e.payload, e.seq
    FROM events e
    WHERE e.process_id = %(process)s
    UNION ALL
    SELECT m.id, m.event_name, m.created_at, m.actor, m.process_id, m.process_state, m.caused_by_event_id,
           m.payload, m.seq
    FROM events m
    WHERE m.process_id IS NULL
      AND m.event_name = %(message)s
      AND m.id IN (SELECT caused_by_event_id FROM events WHERE process_id = %(process)s)
    ORDER BY 9
    """


class PostgresConsultantCases:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def queue(self) -> list[QueueItem]:
        rows = self._conn.execute(QUEUE, {"taken": THREAD_TAKEN}).fetchall()
        return [queue_item(row) for row in rows]

    def handoff(self, process_id: UUID) -> HandoffSource | None:
        return self._handoff(HANDOFF, process_id)

    # The close stamps the state it read, so the row stays put until the close commits.
    def lock_handoff(self, process_id: UUID) -> HandoffSource | None:
        return self._handoff(HANDOFF + " FOR SHARE OF p", process_id)

    def trace(self, process_id: UUID) -> list[TraceRecord] | None:
        if self._conn.execute("SELECT 1 FROM processes WHERE id = %s", (process_id,)).fetchone() is None:
            return None
        rows = self._conn.execute(TRACE, {"process": process_id, "message": MESSAGE_RECEIVED}).fetchall()
        return [trace_record(row) for row in rows]

    def case(self, process_id: UUID) -> CaseRow | None:
        row = self._conn.execute(
            "SELECT id, customer_id, state, end_reason, product, locale FROM processes WHERE id = %s", (process_id,)
        ).fetchone()
        return None if row is None else case_row(row)

    def _handoff(self, query: LiteralString, process_id: UUID) -> HandoffSource | None:
        params = {"analysis": ANALYSIS_COMPLETED, "taken": THREAD_TAKEN, "process": process_id}
        row = self._conn.execute(query, params).fetchone()
        return None if row is None else handoff_source(row)


def stored_event(event_id: UUID | None, payload: Payload | None) -> StoredEvent | None:
    if event_id is None or payload is None:
        return None
    return StoredEvent(event_id, payload)


def queue_item(row: tuple[UUID, str, str, str, str | None, str, UUID | None, Payload | None]) -> QueueItem:
    process_id, customer_id, first_name, last_name, product, locale, taken_id, taken = row
    return QueueItem(
        process_id=process_id,
        customer_id=customer_id,
        first_name=first_name,
        last_name=last_name,
        product=parse_optional_product(product),
        reason_code=handoff_reason(process_id, stored_event(taken_id, taken)),
        locale=parse_member(locale, LOCALES, "locale"),
    )


def handoff_source(
    row: tuple[UUID, str, str, str, str, str, UUID | None, Payload | None, UUID | None, Payload | None],
) -> HandoffSource:
    process_id, customer_id, first_name, last_name, state, locale, analysis_id, analysis, taken_id, taken = row
    return HandoffSource(
        process_id=process_id,
        customer_id=customer_id,
        first_name=first_name,
        last_name=last_name,
        state=parse_state(state),
        locale=parse_member(locale, LOCALES, "locale"),
        analysis=stored_event(analysis_id, analysis),
        thread_taken=stored_event(taken_id, taken),
    )


def trace_record(row: tuple[UUID, str, datetime, str, UUID | None, str, UUID | None, Payload, int]) -> TraceRecord:
    event_id, event_name, created_at, actor, process_id, process_state, caused_by_event_id, payload, _ = row
    return TraceRecord(
        event_id=event_id,
        event_name=parse_member(event_name, EVENT_NAMES, "event_name"),
        created_at=created_at,
        actor=parse_member(actor, ACTORS, "actor"),
        process_id=process_id,
        process_state=parse_state(process_state),
        caused_by_event_id=caused_by_event_id,
        payload=payload,
    )
