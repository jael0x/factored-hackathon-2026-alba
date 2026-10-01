import psycopg

from api.domain.customers.identity import CustomerHit, CustomerIdentity
from api.infrastructure.db.search import SEARCH_LIMIT, escape_like


class PostgresCustomers:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def find_by_document(self, document_number: str) -> CustomerIdentity | None:
        row = self._conn.execute(
            "SELECT customer_id, first_name, last_name, email FROM customers WHERE document_number = %s",
            (document_number,),
        ).fetchone()
        return CustomerIdentity(*row) if row else None

    def find_by_id(self, customer_id: str) -> CustomerIdentity | None:
        row = self._conn.execute(
            "SELECT customer_id, first_name, last_name, email FROM customers WHERE customer_id = %s",
            (customer_id,),
        ).fetchone()
        return CustomerIdentity(*row) if row else None

    def search(self, query: str) -> list[CustomerHit]:
        needle = escape_like(query.strip())
        rows = self._conn.execute(
            """
            SELECT customer_id, document_number, first_name, last_name, country
            FROM customers
            WHERE first_name || ' ' || last_name ILIKE '%%' || %(needle)s || '%%'
               OR document_number LIKE %(needle)s || '%%'
               OR customer_id ILIKE %(needle)s || '%%'
            ORDER BY last_name, first_name, customer_id
            LIMIT %(limit)s
            """,
            {"needle": needle, "limit": SEARCH_LIMIT},
        ).fetchall()
        return [_hit(row) for row in rows]

    def pick_random_with_email(self) -> list[CustomerHit]:
        rows = self._conn.execute(
            """
            SELECT customer_id, document_number, first_name, last_name, country
            FROM customers
            WHERE email IS NOT NULL
            ORDER BY random()
            LIMIT 1
            """
        ).fetchall()
        return [_hit(row) for row in rows]


def _hit(row: tuple[str, str, str, str, str]) -> CustomerHit:
    customer_id, document_number, first_name, last_name, country = row
    return CustomerHit(
        customer_id=customer_id,
        document_number=document_number,
        first_name=first_name,
        last_name=last_name,
        country=country,
    )
