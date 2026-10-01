from dataclasses import dataclass

import psycopg

from api.contract_models import AgentSearchHit, CurrentAgent
from api.search import SEARCH_LIMIT, like_escape

ACTIVE_STATUS = "Active"


@dataclass(frozen=True)
class AgentLogin:
    agent_id: str
    email: str


def normalize_email(value: str) -> str:
    return value.strip().lower()


def normalize_employee_code(value: str) -> str:
    return value.strip().upper()


def find_active_by_login(conn: psycopg.Connection, email: str, employee_code: str) -> AgentLogin | None:
    row = conn.execute(
        """
        SELECT agent_id, email
        FROM service_agents
        WHERE lower(email) = %s AND upper(employee_code) = %s AND agent_status = %s
        """,
        (normalize_email(email), normalize_employee_code(employee_code), ACTIVE_STATUS),
    ).fetchone()
    return AgentLogin(*row) if row else None


def find_by_id(conn: psycopg.Connection, agent_id: str) -> CurrentAgent | None:
    row = conn.execute(
        "SELECT agent_id, employee_code, first_name, last_name, specialty FROM service_agents WHERE agent_id = %s",
        (agent_id,),
    ).fetchone()
    if row is None:
        return None
    agent_id, employee_code, first_name, last_name, specialty = row
    return CurrentAgent(
        agent_id=agent_id,
        employee_code=employee_code,
        first_name=first_name,
        last_name=last_name,
        specialty=specialty,
    )


def search_active(conn: psycopg.Connection, query: str) -> list[AgentSearchHit]:
    rows = conn.execute(
        """
        SELECT agent_id, employee_code, first_name, last_name, email
        FROM service_agents
        WHERE agent_status = %(active)s
          AND (
            first_name || ' ' || last_name ILIKE '%%' || %(needle)s || '%%'
            OR employee_code ILIKE %(needle)s || '%%'
            OR agent_id ILIKE %(needle)s || '%%'
          )
        ORDER BY last_name, first_name, agent_id
        LIMIT %(limit)s
        """,
        {"active": ACTIVE_STATUS, "needle": like_escape(query.strip()), "limit": SEARCH_LIMIT},
    ).fetchall()
    return [_hit(row) for row in rows]


def pick_random_active(conn: psycopg.Connection) -> list[AgentSearchHit]:
    rows = conn.execute(
        """
        SELECT agent_id, employee_code, first_name, last_name, email
        FROM service_agents
        WHERE agent_status = %s
        ORDER BY random()
        LIMIT 1
        """,
        (ACTIVE_STATUS,),
    ).fetchall()
    return [_hit(row) for row in rows]


def _hit(row: tuple[str, str, str, str, str]) -> AgentSearchHit:
    agent_id, employee_code, first_name, last_name, email = row
    return AgentSearchHit(
        agent_id=agent_id,
        employee_code=employee_code,
        first_name=first_name,
        last_name=last_name,
        email=email,
    )
