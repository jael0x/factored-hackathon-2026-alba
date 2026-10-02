import psycopg

from api.domain.consultants.identity import ConsultantHit, ConsultantIdentity
from api.domain.consultants.login import ACTIVE_STATUS, ConsultantLoginKey
from api.infrastructure.db.search import SEARCH_LIMIT, escape_like


class PostgresConsultants:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def find_by_login(self, key: ConsultantLoginKey) -> ConsultantIdentity | None:
        row = self._conn.execute(
            """
            SELECT agent_id, employee_code, first_name, last_name, email, agent_status, specialty
            FROM service_agents
            WHERE lower(email) = %s AND upper(employee_code) = %s
            """,
            (key.email, key.employee_code),
        ).fetchone()
        return ConsultantIdentity(*row) if row else None

    def find_by_id(self, consultant_id: str) -> ConsultantIdentity | None:
        row = self._conn.execute(
            """
            SELECT agent_id, employee_code, first_name, last_name, email, agent_status, specialty
            FROM service_agents
            WHERE agent_id = %s
            """,
            (consultant_id,),
        ).fetchone()
        return ConsultantIdentity(*row) if row else None

    def search_active(self, query: str) -> list[ConsultantHit]:
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
        return [ConsultantHit(*row) for row in rows]

    def pick_random_active(self) -> list[ConsultantHit]:
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
        return [ConsultantHit(*row) for row in rows]
