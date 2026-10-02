from collections.abc import Callable
from pathlib import Path

import psycopg
import pytest

from pipeline.migrate import FORMER_NAMES, apply_migrations

pytestmark = pytest.mark.integration

MIGRATE_TEST_DB = "alba_migrate_test"
MIGRATIONS = Path(__file__).resolve().parents[2] / "db" / "migrations"
RENAMED = "003_consultant_login.sql"


def test_a_migration_recorded_under_its_former_name_is_not_run_again(
    migrated_database: Callable[[str], str], monkeypatch: pytest.MonkeyPatch
) -> None:
    url = migrated_database(MIGRATE_TEST_DB)
    with psycopg.connect(url) as conn:
        conn.execute("UPDATE schema_migrations SET filename = %s WHERE filename = %s", (FORMER_NAMES[RENAMED], RENAMED))
        conn.execute(
            """
            INSERT INTO service_agents (agent_id, employee_code, first_name, last_name, email, agent_status)
            VALUES ('AGT-OJ9N4FGYV9', 'E75612', 'César', 'González Sánchez', 'cesar.gonzalez@example.com', 'Active')
            """
        )
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("MIGRATIONS_DIR", str(MIGRATIONS))

    apply_migrations()

    with psycopg.connect(url) as conn:
        recorded = {row[0] for row in conn.execute("SELECT filename FROM schema_migrations")}
        service_agents = conn.execute("SELECT agent_id FROM service_agents").fetchall()
    assert recorded == {path.name for path in MIGRATIONS.glob("*.sql")} | {FORMER_NAMES[RENAMED]}
    assert service_agents == [("AGT-OJ9N4FGYV9",)]
