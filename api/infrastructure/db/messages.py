from uuid import UUID

import psycopg

from api.contract_models import MessageAuthor


class PostgresThread:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def add_line(self, process_id: UUID, author: MessageAuthor, body: str, event_id: UUID) -> None:
        self._conn.execute(
            "INSERT INTO messages (process_id, author, body, event_id) VALUES (%s, %s, %s, %s)",
            (process_id, author, body, event_id),
        )
