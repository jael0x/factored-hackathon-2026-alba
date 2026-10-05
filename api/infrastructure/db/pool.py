from psycopg_pool import ConnectionPool

from api.infrastructure.db.json_codec import configure_json


def open_pool(database_url: str, min_size: int, max_size: int) -> ConnectionPool:
    pool = ConnectionPool(
        conninfo=database_url, min_size=min_size, max_size=max_size, open=False, configure=configure_json
    )
    pool.open(wait=False)
    return pool


def ping(pool: ConnectionPool) -> None:
    with pool.connection() as conn:
        conn.execute("SELECT 1")
