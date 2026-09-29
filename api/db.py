import psycopg

from api.settings import settings


def connect() -> psycopg.Connection:
    return psycopg.connect(settings.database_url)


def ping() -> None:
    with connect() as conn:
        conn.execute("SELECT 1")
