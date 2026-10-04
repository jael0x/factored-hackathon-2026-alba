from collections.abc import Callable
from pathlib import Path

import psycopg
import pytest
from psycopg.types.json import Jsonb

from pipeline.migrate import FORMER_NAMES, apply_migrations

pytestmark = pytest.mark.integration

MIGRATE_TEST_DB = "alba_migrate_test"
MIGRATIONS = Path(__file__).resolve().parents[2] / "db" / "migrations"
RENAMED = "003_consultant_login.sql"
EVENTS_LOCALE_CHECK = "008_events_locale_check.sql"


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


def database_before_events_locale_check(migrated_database: Callable[[str], str], locale: str) -> str:
    url = migrated_database(MIGRATE_TEST_DB)
    with psycopg.connect(url) as conn:
        conn.execute("ALTER TABLE events DROP CONSTRAINT events_locale_check")
        conn.execute("DELETE FROM schema_migrations WHERE filename = %s", (EVENTS_LOCALE_CHECK,))
        conn.execute(
            """
            INSERT INTO events (event_name, payload, customer_id, actor, idempotency_key)
            VALUES ('conversation.message_received', %s, 'CLI-9EDEKZ8OUNUR', 'customer', 'msg:test')
            """,
            (Jsonb({"text": "quiero una tarjeta", "locale": locale}),),
        )
    return url


def test_a_database_holding_an_english_event_is_not_loaded(
    migrated_database: Callable[[str], str], monkeypatch: pytest.MonkeyPatch
) -> None:
    url = database_before_events_locale_check(migrated_database, "en")
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("MIGRATIONS_DIR", str(MIGRATIONS))

    with pytest.raises(psycopg.errors.CheckViolation, match="events_locale_check"):
        apply_migrations()

    with psycopg.connect(url) as conn:
        recorded = {row[0] for row in conn.execute("SELECT filename FROM schema_migrations")}
    assert EVENTS_LOCALE_CHECK not in recorded


def test_a_database_holding_only_supported_locales_takes_the_check(
    migrated_database: Callable[[str], str], monkeypatch: pytest.MonkeyPatch
) -> None:
    url = database_before_events_locale_check(migrated_database, "pt")
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("MIGRATIONS_DIR", str(MIGRATIONS))

    apply_migrations()

    with psycopg.connect(url) as conn:
        recorded = {row[0] for row in conn.execute("SELECT filename FROM schema_migrations")}
    assert EVENTS_LOCALE_CHECK in recorded

    english = Jsonb({"text": "I want a card", "locale": "en"})
    with psycopg.connect(url) as conn, pytest.raises(psycopg.errors.CheckViolation, match="events_locale_check"):
        conn.execute(
            """
            INSERT INTO events (event_name, payload, customer_id, actor, idempotency_key)
            VALUES ('conversation.message_received', %s, 'CLI-9EDEKZ8OUNUR', 'customer', 'msg:test-en')
            """,
            (english,),
        )
