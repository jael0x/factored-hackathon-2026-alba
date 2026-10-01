from datetime import datetime
from uuid import UUID

import psycopg

from api.domain.session.codes import CODE_TTL, IssuedCode
from api.domain.session.tokens import Role


class PostgresLoginCodes:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def store(self, subject_id: str, role: Role, code_hash: str, now: datetime) -> None:
        self._conn.execute(
            "INSERT INTO login_codes (subject_id, role, code_hash, expires_at, created_at) VALUES (%s, %s, %s, %s, %s)",
            (subject_id, role, code_hash, now + CODE_TTL, now),
        )

    def latest(self, subject_id: str, role: Role) -> IssuedCode | None:
        row = self._conn.execute(
            """
            SELECT id, code_hash, expires_at, wrong_codes, used_at
            FROM login_codes
            WHERE subject_id = %s AND role = %s
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (subject_id, role),
        ).fetchone()
        return IssuedCode(*row) if row else None

    def record_wrong(self, code_id: UUID) -> None:
        self._conn.execute("UPDATE login_codes SET wrong_codes = wrong_codes + 1 WHERE id = %s", (code_id,))

    def spend(self, code_id: UUID, now: datetime) -> bool:
        row = self._conn.execute(
            "UPDATE login_codes SET used_at = %s WHERE id = %s AND used_at IS NULL RETURNING id",
            (now, code_id),
        ).fetchone()
        return row is not None
