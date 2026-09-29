import os
import time
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg


def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is missing")
    return url


def wait_for_postgres(timeout_seconds: int = 120) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with psycopg.connect(database_url(), connect_timeout=5) as conn:
                conn.execute("SELECT 1")
            return
        except Exception as exc:  # noqa: BLE001 - retry until deadline
            last_error = exc
            time.sleep(2)
    raise SystemExit(f"Postgres not ready: {last_error}")


@contextmanager
def connect() -> Iterator[psycopg.Connection]:
    with psycopg.connect(database_url(), autocommit=False) as conn:
        yield conn
