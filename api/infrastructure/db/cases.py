from uuid import UUID

import psycopg

from api.domain.closed_sets import parse_member
from api.domain.process.case import CertificateView, ThreadLine, certificate_of
from api.domain.process.events import ANALYSIS_COMPLETED, MESSAGE_RECEIVED, PREQUALIFICATION_DECIDED
from api.domain.process.stored_events import parse_optional_product
from api.domain.process.thread import CUSTOMER_AUTHOR, MESSAGE_AUTHORS


class PostgresThreads:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    # Customer lines are the process's messages, plus each message with no process that an event of the process
    # names as its cause. Assistant and template lines are messages rows. All follow the seq of their event.
    def thread(self, customer_id: str, process_id: UUID) -> list[ThreadLine]:
        rows = self._conn.execute(
            """
            SELECT e.id, %(customer_author)s, e.payload->>'text', e.id, e.seq
            FROM events e
            WHERE e.event_name = %(message)s
              AND e.customer_id = %(customer_id)s
              AND (
                e.process_id = %(process)s
                OR (e.process_id IS NULL AND e.id IN (
                    SELECT caused_by_event_id FROM events WHERE process_id = %(process)s
                ))
              )
            UNION ALL
            SELECT m.id, m.author, m.body, m.event_id, e.seq
            FROM messages m
            JOIN events e ON e.id = m.event_id
            JOIN processes p ON p.id = m.process_id
            WHERE m.process_id = %(process)s AND p.customer_id = %(customer_id)s
            ORDER BY 5
            """,
            {
                "customer_author": CUSTOMER_AUTHOR,
                "message": MESSAGE_RECEIVED,
                "process": process_id,
                "customer_id": customer_id,
            },
        ).fetchall()
        return [
            ThreadLine(line_id, parse_member(author, MESSAGE_AUTHORS, "author"), body, event_id)
            for line_id, author, body, event_id, _ in rows
        ]

    # The case's certificate is its latest decision; seq is unique, so the latest is one row.
    def certificate(self, customer_id: str, process_id: UUID) -> CertificateView | None:
        row = self._conn.execute(
            """
            SELECT d.id, d.payload, a.payload, p.product
            FROM events d
            JOIN processes p ON p.id = d.process_id
            LEFT JOIN events a ON a.id = d.caused_by_event_id AND a.event_name = %(analysis)s
            WHERE d.process_id = %(process)s AND p.customer_id = %(customer_id)s AND d.event_name = %(decided)s
            ORDER BY d.seq DESC
            LIMIT 1
            """,
            {
                "analysis": ANALYSIS_COMPLETED,
                "decided": PREQUALIFICATION_DECIDED,
                "process": process_id,
                "customer_id": customer_id,
            },
        ).fetchone()
        if row is None:
            return None
        event_id, decided, analysis, product = row
        return certificate_of(event_id, decided, analysis, parse_optional_product(product))
