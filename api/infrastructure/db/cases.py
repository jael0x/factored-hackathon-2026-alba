from collections.abc import Mapping
from datetime import date
from decimal import Decimal
from uuid import UUID

import psycopg

from api.domain.closed_sets import parse_member
from api.domain.locale import LOCALES
from api.domain.policy.engine import INCOME_CURRENCY, INCOME_LOCAL, INCOME_USD
from api.domain.process.case import CertificateView, ThreadLine
from api.domain.process.events import ANALYSIS_COMPLETED, MESSAGE_RECEIVED, PREQUALIFICATION_DECIDED
from api.domain.process.stored_events import (
    CLOSE_OUTCOMES,
    DECIDED_BY,
    INCOME_CURRENCIES,
    field,
    parse_optional_product,
)
from api.domain.process.thread import CUSTOMER_AUTHOR, MESSAGE_AUTHORS


class PostgresThreads:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    # Customer lines are the process's messages, plus each message with no process that an event of the process
    # names as its cause. Assistant and template lines are messages rows. All follow the seq of their event.
    def thread(self, process_id: UUID) -> list[ThreadLine]:
        rows = self._conn.execute(
            """
            SELECT e.id, %(customer_author)s, e.payload->>'text', e.id, e.seq
            FROM events e
            WHERE e.event_name = %(message)s
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
            WHERE m.process_id = %(process)s
            ORDER BY 5
            """,
            {"customer_author": CUSTOMER_AUTHOR, "message": MESSAGE_RECEIVED, "process": process_id},
        ).fetchall()
        return [
            ThreadLine(line_id, parse_member(author, MESSAGE_AUTHORS, "author"), body, event_id)
            for line_id, author, body, event_id, _ in rows
        ]

    # The certificate is the latest decision's text, with the income facts of the latest analysis (D24 (7)).
    def certificate(self, process_id: UUID) -> CertificateView | None:
        latest = self._latest(process_id, PREQUALIFICATION_DECIDED)
        if latest is None:
            return None
        event_id, decided = latest
        analysis = (self._latest(process_id, ANALYSIS_COMPLETED) or (event_id, {}))[1]
        facts = facts_by_name(analysis.get("facts"))
        income = facts.get(INCOME_LOCAL, {})
        currency = facts.get(INCOME_CURRENCY, {}).get("value")
        as_of = income.get("as_of")
        return CertificateView(
            event_id=event_id,
            decided_by=parse_member(field(decided, "decided_by"), DECIDED_BY, "decided_by"),
            locale=parse_member(field(decided, "locale"), LOCALES, "locale"),
            outcome=parse_member(field(decided, "outcome"), CLOSE_OUTCOMES, "outcome"),
            body=str(field(decided, "body")),
            product=parse_optional_product(analysis.get("product")),
            income_local=amount(income.get("value")),
            income_currency=None if currency is None else parse_member(currency, INCOME_CURRENCIES, "income_currency"),
            income_usd=amount(facts.get(INCOME_USD, {}).get("value")),
            as_of=None if as_of is None else date.fromisoformat(str(as_of)),
        )

    def _latest(self, process_id: UUID, event_name: str) -> tuple[UUID, Mapping[str, object]] | None:
        row = self._conn.execute(
            "SELECT id, payload FROM events WHERE process_id = %s AND event_name = %s ORDER BY seq DESC LIMIT 1",
            (process_id, event_name),
        ).fetchone()
        return None if row is None else (row[0], row[1])


def facts_by_name(value: object) -> dict[str, Mapping[str, object]]:
    if not isinstance(value, list):
        return {}
    return {str(item["name"]): item for item in value if isinstance(item, dict)}


def amount(value: object) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, (int, Decimal)) and not isinstance(value, bool):
        return Decimal(value)
    raise TypeError(f"an income fact is a number, got {type(value).__name__}")
