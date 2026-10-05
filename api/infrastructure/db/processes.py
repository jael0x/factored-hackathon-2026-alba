from uuid import UUID

import psycopg
from psycopg import sql

from api.contract_models import EndReason, Locale, ProcessKey, ProcessState, ProductKey
from api.domain.closed_sets import parse_member
from api.domain.process.lifecycle import AI_ACTIVE, ENDED, ProcessRow, parse_state
from api.domain.process.stored_events import PRODUCT_KEYS

INSERT_OPEN = sql.SQL(
    """
    INSERT INTO processes (customer_id, process_key, state, locale)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (customer_id, process_key) WHERE state <> {ended} DO NOTHING
    RETURNING id
    """
).format(ended=sql.Literal(ENDED))


class PostgresProcesses:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def find_open(self, customer_id: str, process_key: ProcessKey) -> ProcessRow | None:
        row = self._conn.execute(
            """
            SELECT id, customer_id, state
            FROM processes
            WHERE customer_id = %s AND process_key = %s AND state <> %s
            FOR SHARE
            """,
            (customer_id, process_key, ENDED),
        ).fetchone()
        return process_row(row) if row else None

    def insert_open(self, customer_id: str, process_key: ProcessKey, locale: Locale) -> UUID | None:
        row = self._conn.execute(INSERT_OPEN, (customer_id, process_key, AI_ACTIVE, locale)).fetchone()
        return row[0] if row else None

    def lock(self, process_id: UUID) -> ProcessRow | None:
        row = self._conn.execute(
            "SELECT id, customer_id, state FROM processes WHERE id = %s FOR UPDATE", (process_id,)
        ).fetchone()
        return process_row(row) if row else None

    def read(self, process_id: UUID) -> ProcessRow | None:
        row = self._conn.execute("SELECT id, customer_id, state FROM processes WHERE id = %s", (process_id,)).fetchone()
        return process_row(row) if row else None

    def product_of(self, process_id: UUID) -> ProductKey | None:
        row = self._conn.execute("SELECT product FROM processes WHERE id = %s", (process_id,)).fetchone()
        if row is None:
            raise LookupError(f"process {process_id} does not exist")
        return None if row[0] is None else parse_member(row[0], PRODUCT_KEYS, "product")

    def store_turn_facts(self, process_id: UUID, locale: Locale, product: ProductKey | None) -> None:
        self._conn.execute(
            "UPDATE processes SET locale = %s, product = COALESCE(%s, product) WHERE id = %s",
            (locale, product, process_id),
        )

    def set_state(self, process_id: UUID, state: ProcessState, end_reason: EndReason | None) -> None:
        self._conn.execute(
            "UPDATE processes SET state = %s, end_reason = %s WHERE id = %s", (state, end_reason, process_id)
        )


def process_row(row: tuple[UUID, str, str]) -> ProcessRow:
    process_id, customer_id, state = row
    return ProcessRow(process_id=process_id, customer_id=customer_id, state=parse_state(state))
