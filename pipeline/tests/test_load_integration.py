import os
from pathlib import Path

import psycopg
import pytest

from pipeline.batches import all_hashes_loaded, new_batch_id, record_batches
from pipeline.bronze import BronzeFile, file_sha256
from pipeline.gold import rebuild_gold
from pipeline.migrate import apply_migrations
from pipeline.silver import reload_silver

pytestmark = pytest.mark.integration

ADMIN_URL = os.environ.get(
    "ALBA_TEST_ADMIN_DATABASE_URL",
    "postgresql://alba:alba@127.0.0.1:55432/postgres",
)
TEST_DB = os.environ.get("ALBA_TEST_DATABASE_NAME", "alba_test")
TEST_URL = os.environ.get(
    "ALBA_TEST_DATABASE_URL",
    f"postgresql://alba:alba@127.0.0.1:55432/{TEST_DB}",
)


def _bronze(path: Path) -> BronzeFile:
    return BronzeFile(
        relative_name=path.name,
        path=path,
        bytes=path.stat().st_size,
        sha256=file_sha256(path),
    )


def _postgres_available() -> bool:
    try:
        with psycopg.connect(ADMIN_URL, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def test_database_url() -> str:
    if not _postgres_available():
        pytest.skip("Postgres not reachable for integration tests")
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (TEST_DB,),
        ).fetchone()
        if not exists:
            conn.execute(f'CREATE DATABASE "{TEST_DB}"')
        else:
            conn.execute(
                """
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = %s AND pid <> pg_backend_pid()
                """,
                (TEST_DB,),
            )
            conn.execute(f'DROP DATABASE "{TEST_DB}"')
            conn.execute(f'CREATE DATABASE "{TEST_DB}"')
    return TEST_URL


@pytest.fixture
def migrated_db(test_database_url: str, monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("MIGRATIONS_DIR", str(root / "db" / "migrations"))
    apply_migrations()
    return test_database_url


def test_migration_creates_core_tables(migrated_db: str) -> None:
    with psycopg.connect(migrated_db) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                """
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
                """
            )
        }
    expected = {
        "customers",
        "products",
        "daily_exchange_rates",
        "service_agents",
        "customer_credit_profile",
        "load_batches",
        "events",
        "processes",
        "commands",
        "messages",
        "llm_turns",
        "login_codes",
        "schema_migrations",
    }
    assert expected <= tables


def test_silver_gold_and_idempotent_batch(
    migrated_db: str,
    testdata_dir: Path,
) -> None:
    files = [
        _bronze(testdata_dir / "customers.csv"),
        _bronze(testdata_dir / "products.csv"),
        _bronze(testdata_dir / "daily_exchange_rates.csv"),
        _bronze(testdata_dir / "service_agents.csv"),
    ]
    batch_id = new_batch_id()
    with psycopg.connect(migrated_db) as conn:
        with conn.transaction():
            reload_silver(conn, files)
            rebuild_gold(conn, batch_id)
            record_batches(conn, files, batch_id)

        customers = conn.execute("SELECT COUNT(*) FROM customers").fetchone()
        products = conn.execute("SELECT COUNT(*) FROM products").fetchone()
        gold = conn.execute("SELECT COUNT(*) FROM customer_credit_profile").fetchone()
        assert customers == (3,)
        assert products == (2,)
        assert gold == (3,)

        juan = conn.execute(
            """
            SELECT credit_score, has_active_card, max_days_past_due,
                   income_local, income_currency
            FROM customer_credit_profile
            WHERE customer_id = %s
            """,
            ("CLI-TEST-JUAN",),
        ).fetchone()
        assert juan is not None
        assert juan[0] == 812
        assert juan[1] is False
        assert juan[2] == 0
        assert juan[3] is not None
        assert juan[4] == "MXN"

        mariana = conn.execute(
            """
            SELECT has_active_card, max_days_past_due
            FROM customer_credit_profile
            WHERE customer_id = %s
            """,
            ("CLI-TEST-MARI",),
        ).fetchone()
        assert mariana == (True, 180)

        juliana = conn.execute(
            """
            SELECT credit_score, income_local
            FROM customer_credit_profile
            WHERE customer_id = %s
            """,
            ("CLI-TEST-JULI",),
        ).fetchone()
        assert juliana == (None, None)

        assert all_hashes_loaded(conn, files) is True

        first_batch = conn.execute(
            "SELECT batch_id FROM load_batches WHERE path = %s",
            ("customers.csv",),
        ).fetchone()
        assert first_batch is not None
        stored_batch_id = first_batch[0]
        assert stored_batch_id == batch_id

        second_batch_id = new_batch_id()
        with conn.transaction():
            reload_silver(conn, files)
            rebuild_gold(conn, second_batch_id)
            record_batches(conn, files, second_batch_id)
        assert all_hashes_loaded(conn, files) is True
        updated = conn.execute(
            "SELECT batch_id FROM load_batches WHERE path = %s",
            ("customers.csv",),
        ).fetchone()
        assert updated == (second_batch_id,)


def test_changed_file_is_reloaded(
    migrated_db: str,
    testdata_dir: Path,
    tmp_path: Path,
) -> None:
    work = tmp_path / "raw"
    work.mkdir()
    for name in (
        "customers.csv",
        "products.csv",
        "daily_exchange_rates.csv",
        "service_agents.csv",
    ):
        (work / name).write_bytes((testdata_dir / name).read_bytes())

    files = [_bronze(work / name) for name in (
        "customers.csv",
        "products.csv",
        "daily_exchange_rates.csv",
        "service_agents.csv",
    )]
    batch_id = new_batch_id()
    with psycopg.connect(migrated_db) as conn:
        with conn.transaction():
            reload_silver(conn, files)
            rebuild_gold(conn, batch_id)
            record_batches(conn, files, batch_id)
        assert all_hashes_loaded(conn, files) is True

        products_path = work / "products.csv"
        products_path.write_text(
            products_path.read_text(encoding="utf-8-sig")
            + "PRD-3,CLI-TEST-JUAN,Tarjeta Crédito,****1111,USD,10.00,Active,0\n",
            encoding="utf-8",
        )
        changed = [_bronze(work / name) for name in (
            "customers.csv",
            "products.csv",
            "daily_exchange_rates.csv",
            "service_agents.csv",
        )]
        assert all_hashes_loaded(conn, changed) is False

        reload_batch = new_batch_id()
        with conn.transaction():
            reload_silver(conn, changed)
            rebuild_gold(conn, reload_batch)
            record_batches(conn, changed, reload_batch)

        product_count = conn.execute("SELECT COUNT(*) FROM products").fetchone()
        assert product_count == (3,)
        juan = conn.execute(
            """
            SELECT has_active_card FROM customer_credit_profile
            WHERE customer_id = %s
            """,
            ("CLI-TEST-JUAN",),
        ).fetchone()
        assert juan == (True,)
        assert all_hashes_loaded(conn, changed) is True


def test_orphan_product_fails_quality_check(
    migrated_db: str,
    testdata_dir: Path,
    tmp_path: Path,
) -> None:
    work = tmp_path / "raw"
    work.mkdir()
    for name in (
        "customers.csv",
        "daily_exchange_rates.csv",
        "service_agents.csv",
    ):
        (work / name).write_bytes((testdata_dir / name).read_bytes())
    (work / "products.csv").write_text(
        "product_id,customer_id,product_type,product_number,currency,"
        "current_balance,product_status,days_past_due\n"
        "PRD-X,CLI-DOES-NOT-EXIST,Tarjeta Crédito,****0000,USD,1.00,Active,0\n",
        encoding="utf-8",
    )
    files = [_bronze(work / name) for name in (
        "customers.csv",
        "products.csv",
        "daily_exchange_rates.csv",
        "service_agents.csv",
    )]
    with psycopg.connect(migrated_db) as conn:
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            with conn.transaction():
                reload_silver(conn, files)
