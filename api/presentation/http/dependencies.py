from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated, Protocol

import psycopg
from fastapi import Depends, Header, Request
from psycopg_pool import ConnectionPool

from api.application.customers.search_customers import RejectedSearch, search_customers
from api.application.session.issue_code import issue_customer_code
from api.application.session.open_session import open_customer_session
from api.application.session.read_current_customer import read_current_customer
from api.domain.customers.identity import CustomerHit, CustomerIdentity
from api.domain.session.codes import CodeDelivery
from api.domain.session.tokens import CUSTOMER, SessionClaims, read_token
from api.infrastructure.config.settings import settings
from api.infrastructure.db.customers import PostgresCustomers
from api.infrastructure.db.login_codes import PostgresLoginCodes
from api.presentation.http.errors import ApiError, forbidden, unauthorized

BEARER_PREFIX = "Bearer "


class IssueCustomerCode(Protocol):
    def __call__(self, document_number: str) -> CodeDelivery | None: ...


class OpenCustomerSession(Protocol):
    def __call__(self, document_number: str, code: str) -> SessionClaims | None: ...


class ReadCurrentCustomer(Protocol):
    def __call__(self, customer_id: str) -> CustomerIdentity | None: ...


class RunCustomerSearch(Protocol):
    def __call__(self, q: str | None, random: bool | None) -> list[CustomerHit] | RejectedSearch: ...


def get_connection(request: Request) -> Iterator[psycopg.Connection]:
    pool: ConnectionPool = request.app.state.pool
    with pool.connection() as conn:
        try:
            yield conn
        except ApiError:
            conn.commit()
            raise


def get_now() -> datetime:
    return datetime.now(UTC)


def get_jwt_secret() -> str:
    return settings.jwt_secret


def get_demo_login() -> bool:
    return settings.demo_login


def get_issue_customer_code(
    conn: Annotated[psycopg.Connection, Depends(get_connection)],
    secret: Annotated[str, Depends(get_jwt_secret)],
    now: Annotated[datetime, Depends(get_now)],
) -> IssueCustomerCode:
    customers = PostgresCustomers(conn)
    login_codes = PostgresLoginCodes(conn)

    def issue(document_number: str) -> CodeDelivery | None:
        return issue_customer_code(customers, login_codes, secret, document_number, now)

    return issue


def get_open_customer_session(
    conn: Annotated[psycopg.Connection, Depends(get_connection)],
    secret: Annotated[str, Depends(get_jwt_secret)],
    now: Annotated[datetime, Depends(get_now)],
) -> OpenCustomerSession:
    customers = PostgresCustomers(conn)
    login_codes = PostgresLoginCodes(conn)

    def open_session(document_number: str, code: str) -> SessionClaims | None:
        return open_customer_session(customers, login_codes, secret, document_number, code, now)

    return open_session


def get_read_current_customer(
    conn: Annotated[psycopg.Connection, Depends(get_connection)],
) -> ReadCurrentCustomer:
    customers = PostgresCustomers(conn)

    def read(customer_id: str) -> CustomerIdentity | None:
        return read_current_customer(customers, customer_id)

    return read


def get_run_customer_search(request: Request) -> RunCustomerSearch:
    def run(q: str | None, random: bool | None) -> list[CustomerHit] | RejectedSearch:
        pool: ConnectionPool = request.app.state.pool
        with pool.connection() as conn:
            return search_customers(PostgresCustomers(conn), q, random)

    return run


def get_session(authorization: Annotated[str | None, Header()] = None) -> SessionClaims:
    if authorization is None or not authorization.startswith(BEARER_PREFIX):
        raise unauthorized()
    claims = read_token(settings.jwt_secret, authorization.removeprefix(BEARER_PREFIX))
    if claims is None:
        raise unauthorized()
    return claims


def require_customer(session: Annotated[SessionClaims, Depends(get_session)]) -> SessionClaims:
    if session.role != CUSTOMER:
        raise forbidden()
    return session
