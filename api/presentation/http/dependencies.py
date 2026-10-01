from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from typing import Annotated, Protocol

import psycopg
from fastapi import Depends, Header, Request
from psycopg_pool import ConnectionPool

from api.application.consultants.search_consultants import search_consultants
from api.application.customers.search_customers import search_customers
from api.application.session.issue_code import issue_consultant_code, issue_customer_code
from api.application.session.open_session import open_consultant_session, open_customer_session
from api.application.session.read_current_consultant import read_current_consultant
from api.application.session.read_current_customer import read_current_customer
from api.domain.consultants.identity import ConsultantHit, ConsultantIdentity
from api.domain.customers.identity import CustomerHit, CustomerIdentity
from api.domain.search import RejectedSearch
from api.domain.session.codes import CodeDelivery
from api.domain.session.tokens import CONSULTANT, CUSTOMER, Role, SessionClaims, read_token
from api.infrastructure.config.settings import settings
from api.infrastructure.db.consultants import PostgresConsultants
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


class IssueConsultantCode(Protocol):
    def __call__(self, email: str, employee_code: str) -> CodeDelivery | None: ...


class OpenConsultantSession(Protocol):
    def __call__(self, email: str, employee_code: str, code: str) -> SessionClaims | None: ...


class ReadCurrentConsultant(Protocol):
    def __call__(self, consultant_id: str) -> ConsultantIdentity | None: ...


class RunConsultantSearch(Protocol):
    def __call__(self, q: str | None, random: bool | None) -> list[ConsultantHit] | RejectedSearch: ...


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


def get_issue_consultant_code(
    conn: Annotated[psycopg.Connection, Depends(get_connection)],
    secret: Annotated[str, Depends(get_jwt_secret)],
    now: Annotated[datetime, Depends(get_now)],
) -> IssueConsultantCode:
    consultants = PostgresConsultants(conn)
    login_codes = PostgresLoginCodes(conn)

    def issue(email: str, employee_code: str) -> CodeDelivery | None:
        return issue_consultant_code(consultants, login_codes, secret, email, employee_code, now)

    return issue


def get_open_consultant_session(
    conn: Annotated[psycopg.Connection, Depends(get_connection)],
    secret: Annotated[str, Depends(get_jwt_secret)],
    now: Annotated[datetime, Depends(get_now)],
) -> OpenConsultantSession:
    consultants = PostgresConsultants(conn)
    login_codes = PostgresLoginCodes(conn)

    def open_session(email: str, employee_code: str, code: str) -> SessionClaims | None:
        return open_consultant_session(consultants, login_codes, secret, email, employee_code, code, now)

    return open_session


def get_read_current_consultant(
    conn: Annotated[psycopg.Connection, Depends(get_connection)],
) -> ReadCurrentConsultant:
    consultants = PostgresConsultants(conn)

    def read(consultant_id: str) -> ConsultantIdentity | None:
        return read_current_consultant(consultants, consultant_id)

    return read


def get_run_consultant_search(request: Request) -> RunConsultantSearch:
    def run(q: str | None, random: bool | None) -> list[ConsultantHit] | RejectedSearch:
        pool: ConnectionPool = request.app.state.pool
        with pool.connection() as conn:
            return search_consultants(PostgresConsultants(conn), q, random)

    return run


def get_session(authorization: Annotated[str | None, Header()] = None) -> SessionClaims:
    if authorization is None or not authorization.startswith(BEARER_PREFIX):
        raise unauthorized()
    claims = read_token(settings.jwt_secret, authorization.removeprefix(BEARER_PREFIX))
    if claims is None:
        raise unauthorized()
    return claims


def require_role(role: Role) -> Callable[[SessionClaims], SessionClaims]:
    def check(session: Annotated[SessionClaims, Depends(get_session)]) -> SessionClaims:
        if session.role != role:
            raise forbidden()
        return session

    return check


require_customer = require_role(CUSTOMER)
require_consultant = require_role(CONSULTANT)
