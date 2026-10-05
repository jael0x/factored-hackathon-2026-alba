from uuid import UUID

import psycopg
from psycopg import sql

from api.contract_models import EndReason, Locale, ProcessKey, ProcessState, ProductKey
from api.domain.closed_sets import parse_member
from api.domain.locale import LOCALES
from api.domain.process.case import CaseRow
from api.domain.process.lifecycle import AI_ACTIVE, END_REASONS, ENDED, ProcessRow, parse_state
from api.domain.process.stored_events import PRODUCT_KEYS

INSERT_OPEN = sql.SQL(
    """
    INSERT INTO processes (customer_id, process_key, state, locale, product)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (customer_id, process_key, product) WHERE state <> {ended} DO NOTHING
    RETURNING id
    """
).format(ended=sql.Literal(ENDED))


class PostgresProcesses:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def find_open(self, customer_id: str, process_key: ProcessKey, product: ProductKey) -> ProcessRow | None:
        row = self._conn.execute(
            """
            SELECT id, customer_id, state
            FROM processes
            WHERE customer_id = %s AND process_key = %s AND product = %s AND state <> %s
            FOR SHARE
            """,
            (customer_id, process_key, product, ENDED),
        ).fetchone()
        return process_row(row) if row else None

    # A message reads its case FOR SHARE, so a message sent while the case moves waits and carries the move.
    def read_for_message(self, customer_id: str, process_id: UUID) -> ProcessRow | None:
        row = self._conn.execute(
            "SELECT id, customer_id, state FROM processes WHERE id = %s AND customer_id = %s FOR SHARE",
            (process_id, customer_id),
        ).fetchone()
        return process_row(row) if row else None

    def open_products(self, customer_id: str, except_process_id: UUID) -> frozenset[ProductKey]:
        rows = self._conn.execute(
            """
            SELECT product FROM processes
            WHERE customer_id = %s AND id <> %s AND state <> %s AND product IS NOT NULL
            """,
            (customer_id, except_process_id, ENDED),
        ).fetchall()
        return frozenset(parse_member(product, PRODUCT_KEYS, "product") for (product,) in rows)

    def insert_open(
        self, customer_id: str, process_key: ProcessKey, locale: Locale, product: ProductKey
    ) -> UUID | None:
        row = self._conn.execute(INSERT_OPEN, (customer_id, process_key, AI_ACTIVE, locale, product)).fetchone()
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

    def read_case(self, customer_id: str, process_id: UUID) -> CaseRow | None:
        row = self._conn.execute(
            """
            SELECT id, customer_id, state, end_reason, product, locale
            FROM processes WHERE id = %s AND customer_id = %s
            """,
            (process_id, customer_id),
        ).fetchone()
        return None if row is None else case_row(row)

    def of_customer(self, customer_id: str) -> list[CaseRow]:
        rows = self._conn.execute(
            """
            SELECT id, customer_id, state, end_reason, product, locale
            FROM processes WHERE customer_id = %s ORDER BY created_at DESC, id
            """,
            (customer_id,),
        ).fetchall()
        return [case_row(row) for row in rows]


def process_row(row: tuple[UUID, str, str]) -> ProcessRow:
    process_id, customer_id, state = row
    return ProcessRow(process_id=process_id, customer_id=customer_id, state=parse_state(state))


def case_row(row: tuple[UUID, str, str, str | None, str | None, str]) -> CaseRow:
    found_id, customer_id, state, end_reason, product, locale = row
    return CaseRow(
        process_id=found_id,
        customer_id=customer_id,
        state=parse_state(state),
        end_reason=None if end_reason is None else parse_member(end_reason, END_REASONS, "end_reason"),
        product=None if product is None else parse_member(product, PRODUCT_KEYS, "product"),
        locale=parse_member(locale, LOCALES, "locale"),
    )
