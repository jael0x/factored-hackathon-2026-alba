import psycopg

from api.domain.agents.identity import AgentHit, AgentIdentity
from api.domain.agents.login import ACTIVE_STATUS, AgentLoginKey
from api.infrastructure.db.search import SEARCH_LIMIT, escape_like


class PostgresAgents:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def find_by_login(self, key: AgentLoginKey) -> AgentIdentity | None:
        row = self._conn.execute(
            """
            SELECT agent_id, employee_code, first_name, last_name, email, agent_status, specialty
            FROM service_agents
            WHERE lower(email) = %s AND upper(employee_code) = %s
            """,
            (key.email, key.employee_code),
        ).fetchone()
        return AgentIdentity(*row) if row else None

    def find_by_id(self, agent_id: str) -> AgentIdentity | None:
        row = self._conn.execute(
            """
            SELECT agent_id, employee_code, first_name, last_name, email, agent_status, specialty
            FROM service_agents
            WHERE agent_id = %s
            """,
            (agent_id,),
        ).fetchone()
        return AgentIdentity(*row) if row else None

    def search_active(self, query: str) -> list[AgentHit]:
        rows = self._conn.execute(
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
            {"active": ACTIVE_STATUS, "needle": escape_like(query.strip()), "limit": SEARCH_LIMIT},
        ).fetchall()
        return [AgentHit(*row) for row in rows]

    def pick_random_active(self) -> list[AgentHit]:
        rows = self._conn.execute(
            """
            SELECT agent_id, employee_code, first_name, last_name, email
            FROM service_agents
            WHERE agent_status = %s
            ORDER BY random()
            LIMIT 1
            """,
            (ACTIVE_STATUS,),
        ).fetchall()
        return [AgentHit(*row) for row in rows]
