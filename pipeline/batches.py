from uuid import UUID, uuid4

import psycopg

from pipeline.bronze import BronzeFile


def all_hashes_loaded(conn: psycopg.Connection, files: list[BronzeFile]) -> bool:
    for item in files:
        row = conn.execute(
            """
            SELECT 1 FROM load_batches
            WHERE path = %s AND sha256 = %s
            """,
            (item.relative_name, item.sha256),
        ).fetchone()
        if row is None:
            return False
    return True


def record_batches(conn: psycopg.Connection, files: list[BronzeFile], batch_id: UUID) -> None:
    for item in files:
        conn.execute(
            """
            INSERT INTO load_batches (path, bytes, sha256, batch_id)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (path, sha256) DO UPDATE
            SET batch_id = EXCLUDED.batch_id,
                loaded_at = now(),
                bytes = EXCLUDED.bytes
            """,
            (item.relative_name, item.bytes, item.sha256, str(batch_id)),
        )


def new_batch_id() -> UUID:
    return uuid4()
