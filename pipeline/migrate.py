import os
from pathlib import Path

from pipeline.db import connect


def migrations_dir() -> Path:
    return Path(os.environ.get("MIGRATIONS_DIR", "db/migrations"))


def run_sql_script(conn, script: str) -> None:
    statements = [part.strip() for part in script.split(";") if part.strip()]
    for statement in statements:
        conn.execute(statement)


def apply_migrations() -> None:
    directory = migrations_dir()
    if not directory.is_dir():
        raise SystemExit(f"Migrations directory missing: {directory}")
    files = sorted(directory.glob("*.sql"))
    if not files:
        raise SystemExit(f"No migration files in {directory}")

    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename text PRIMARY KEY,
                applied_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        conn.commit()
        for path in files:
            applied = conn.execute(
                "SELECT 1 FROM schema_migrations WHERE filename = %s",
                (path.name,),
            ).fetchone()
            if applied:
                print(f"migration skip {path.name}")
                continue
            print(f"migration apply {path.name}")
            with conn.transaction():
                run_sql_script(conn, path.read_text(encoding="utf-8"))
                conn.execute(
                    "INSERT INTO schema_migrations (filename) VALUES (%s)",
                    (path.name,),
                )
        conn.commit()
