import os
from pathlib import Path

import psycopg

from pipeline.db import connect

FORMER_NAMES = {"003_consultant_login.sql": "003_agent_login.sql"}


def migrations_dir() -> Path:
    return Path(os.environ.get("MIGRATIONS_DIR", "db/migrations"))


def run_sql_script(conn: psycopg.Connection, script: str) -> None:
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
            applied = applied_names(conn, path.name)
            if path.name in applied:
                print(f"migration skip {path.name}")
                continue
            with conn.transaction():
                if applied:
                    print(f"migration skip {path.name}, applied as {FORMER_NAMES[path.name]}")
                else:
                    print(f"migration apply {path.name}")
                    run_sql_script(conn, path.read_text(encoding="utf-8"))
                conn.execute(
                    "INSERT INTO schema_migrations (filename) VALUES (%s)",
                    (path.name,),
                )
        conn.commit()


def names_of(filename: str) -> list[str]:
    former = FORMER_NAMES.get(filename)
    return [filename] if former is None else [filename, former]


def applied_names(conn: psycopg.Connection, filename: str) -> set[str]:
    rows = conn.execute(
        "SELECT filename FROM schema_migrations WHERE filename = ANY(%s)",
        (names_of(filename),),
    ).fetchall()
    return {row[0] for row in rows}
