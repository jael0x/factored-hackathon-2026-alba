from dataclasses import dataclass

import psycopg

from api.contract_models import CustomerSearchHit
from api.search import SEARCH_LIMIT, like_escape


@dataclass(frozen=True)
class CustomerIdentity:
    customer_id: str
    first_name: str
    last_name: str
    email: str | None


def find_by_document(conn: psycopg.Connection, document_number: str) -> CustomerIdentity | None:
    row = conn.execute(
        "SELECT customer_id, first_name, last_name, email FROM customers WHERE document_number = %s",
        (document_number,),
    ).fetchone()
    return CustomerIdentity(*row) if row else None


def find_by_id(conn: psycopg.Connection, customer_id: str) -> CustomerIdentity | None:
    row = conn.execute(
        "SELECT customer_id, first_name, last_name, email FROM customers WHERE customer_id = %s",
        (customer_id,),
    ).fetchone()
    return CustomerIdentity(*row) if row else None


def search(conn: psycopg.Connection, query: str) -> list[CustomerSearchHit]:
    needle = like_escape(query.strip())
    rows = conn.execute(
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


def pick_random_with_email(conn: psycopg.Connection) -> list[CustomerSearchHit]:
    rows = conn.execute(
        """
        SELECT customer_id, document_number, first_name, last_name, country
        FROM customers
        WHERE email IS NOT NULL
        ORDER BY random()
        LIMIT 1
        """
    ).fetchall()
    return [_hit(row) for row in rows]


def _hit(row: tuple[str, str, str, str, str]) -> CustomerSearchHit:
    customer_id, document_number, first_name, last_name, country = row
    return CustomerSearchHit(
        customer_id=customer_id,
        document_number=document_number,
        first_name=first_name,
        last_name=last_name,
        country=country,
    )
