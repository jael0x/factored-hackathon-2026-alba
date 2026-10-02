import os
from collections.abc import Callable
from pathlib import Path

import psycopg
import pytest
from psycopg import sql

from pipeline.migrate import apply_migrations

ADMIN_URL = os.environ.get("ALBA_TEST_ADMIN_DATABASE_URL", "postgresql://alba:alba@127.0.0.1:55432/postgres")
MIGRATIONS = Path(__file__).resolve().parent / "db" / "migrations"


def _postgres_available() -> bool:
    try:
        with psycopg.connect(ADMIN_URL, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
        return True
    except psycopg.OperationalError:
        return False


def _database_url(name: str) -> str:
    return f"{ADMIN_URL.rsplit('/', 1)[0]}/{name}"


@pytest.fixture(scope="module")
def migrated_database() -> Callable[[str], str]:
    if not _postgres_available():
        if os.environ.get("ALBA_REQUIRE_POSTGRES") == "1":
            pytest.fail(f"Postgres not reachable at {ADMIN_URL} and ALBA_REQUIRE_POSTGRES=1")
        pytest.skip("Postgres not reachable for integration tests")

    def create(name: str) -> str:
        with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
            conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        url = _database_url(name)
        with pytest.MonkeyPatch.context() as patch:
            patch.setenv("DATABASE_URL", url)
            patch.setenv("MIGRATIONS_DIR", str(MIGRATIONS))
            apply_migrations()
        return url

    return create
