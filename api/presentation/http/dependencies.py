from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from typing import Annotated, Protocol

import psycopg
from fastapi import Depends, Header, Request
from psycopg_pool import ConnectionPool

from api.application.agents.search_agents import search_agents
from api.application.customers.search_customers import search_customers
from api.application.session.issue_code import issue_agent_code, issue_customer_code
from api.application.session.open_session import open_agent_session, open_customer_session
from api.application.session.read_current_agent import read_current_agent
from api.application.session.read_current_customer import read_current_customer
from api.domain.agents.identity import AgentHit, AgentIdentity
from api.domain.customers.identity import CustomerHit, CustomerIdentity
from api.domain.search import RejectedSearch
from api.domain.session.codes import CodeDelivery
from api.domain.session.tokens import AGENT, CUSTOMER, Role, SessionClaims, read_token
from api.infrastructure.config.settings import settings
from api.infrastructure.db.agents import PostgresAgents
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


class IssueAgentCode(Protocol):
    def __call__(self, email: str, employee_code: str) -> CodeDelivery | None: ...


class OpenAgentSession(Protocol):
    def __call__(self, email: str, employee_code: str, code: str) -> SessionClaims | None: ...


class ReadCurrentAgent(Protocol):
    def __call__(self, agent_id: str) -> AgentIdentity | None: ...


class RunAgentSearch(Protocol):
    def __call__(self, q: str | None, random: bool | None) -> list[AgentHit] | RejectedSearch: ...


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


def get_issue_agent_code(
    conn: Annotated[psycopg.Connection, Depends(get_connection)],
    secret: Annotated[str, Depends(get_jwt_secret)],
    now: Annotated[datetime, Depends(get_now)],
) -> IssueAgentCode:
    agents = PostgresAgents(conn)
    login_codes = PostgresLoginCodes(conn)

    def issue(email: str, employee_code: str) -> CodeDelivery | None:
        return issue_agent_code(agents, login_codes, secret, email, employee_code, now)

    return issue


def get_open_agent_session(
    conn: Annotated[psycopg.Connection, Depends(get_connection)],
    secret: Annotated[str, Depends(get_jwt_secret)],
    now: Annotated[datetime, Depends(get_now)],
) -> OpenAgentSession:
    agents = PostgresAgents(conn)
    login_codes = PostgresLoginCodes(conn)

    def open_session(email: str, employee_code: str, code: str) -> SessionClaims | None:
        return open_agent_session(agents, login_codes, secret, email, employee_code, code, now)

    return open_session


def get_read_current_agent(
    conn: Annotated[psycopg.Connection, Depends(get_connection)],
) -> ReadCurrentAgent:
    agents = PostgresAgents(conn)

    def read(agent_id: str) -> AgentIdentity | None:
        return read_current_agent(agents, agent_id)

    return read


def get_run_agent_search(request: Request) -> RunAgentSearch:
    def run(q: str | None, random: bool | None) -> list[AgentHit] | RejectedSearch:
        pool: ConnectionPool = request.app.state.pool
        with pool.connection() as conn:
            return search_agents(PostgresAgents(conn), q, random)

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
require_agent = require_role(AGENT)
