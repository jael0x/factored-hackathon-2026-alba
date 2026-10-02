import csv
from pathlib import Path

import psycopg
from psycopg import sql

from pipeline.bronze import BronzeFile
from pipeline.constants import (
    AGENTS_COLUMNS,
    CUSTOMERS_COLUMNS,
    EXCHANGE_COLUMNS,
    PRODUCTS_COLUMNS,
)


TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "customers.csv": CUSTOMERS_COLUMNS,
    "products.csv": PRODUCTS_COLUMNS,
    "daily_exchange_rates.csv": EXCHANGE_COLUMNS,
    "service_agents.csv": AGENTS_COLUMNS,
}

TABLE_NAME: dict[str, str] = {
    "customers.csv": "customers",
    "products.csv": "products",
    "daily_exchange_rates.csv": "daily_exchange_rates",
    "service_agents.csv": "service_agents",
}


INTEGER_COLUMNS = frozenset({"credit_score", "days_past_due"})

EMPTY_AS_ZERO_COLUMNS = frozenset({"current_balance"})


def _empty_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped != "" else None


def coerce_cell(column: str, value: str | None) -> str | int | None:
    cleaned = _empty_to_none(value)
    if cleaned is None:
        return 0 if column in EMPTY_AS_ZERO_COLUMNS else None
    if column in INTEGER_COLUMNS:
        return int(float(cleaned))
    return cleaned


def load_csv_table(
    conn: psycopg.Connection,
    path: Path,
    table: str,
    columns: tuple[str, ...],
) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise SystemExit(f"CSV has no header: {path}")
        missing = [col for col in columns if col not in reader.fieldnames]
        if missing:
            raise SystemExit(
                f"CSV {path.name} missing columns {missing}. "
                f"Found={list(reader.fieldnames)}"
            )
        col_list = sql.SQL(", ").join(sql.Identifier(c) for c in columns)
        copy_sql = sql.SQL("COPY {} ({}) FROM STDIN").format(
            sql.Identifier(table),
            col_list,
        )
        with conn.cursor() as cur:
            with cur.copy(copy_sql) as copy:
                for row in reader:
                    values = [coerce_cell(col, row.get(col)) for col in columns]
                    copy.write_row(values)


def reload_silver(conn: psycopg.Connection, files: list[BronzeFile]) -> None:
    by_name = {item.relative_name: item for item in files}
    with conn.cursor() as cur:
        cur.execute("TRUNCATE customer_credit_profile, products, customers, daily_exchange_rates, service_agents RESTART IDENTITY CASCADE")
    order = (
        "customers.csv",
        "products.csv",
        "daily_exchange_rates.csv",
        "service_agents.csv",
    )
    for name in order:
        item = by_name[name]
        table = TABLE_NAME[name]
        columns = TABLE_COLUMNS[name]
        print(f"silver load {name} -> {table}")
        load_csv_table(conn, item.path, table, columns)

    orphan = conn.execute(
        """
        SELECT COUNT(*) FROM products p
        WHERE NOT EXISTS (
            SELECT 1 FROM customers c WHERE c.customer_id = p.customer_id
        )
        """
    ).fetchone()
    if orphan is None or orphan[0] != 0:
        raise SystemExit(f"Quality check failed: orphan products.customer_id count={orphan}")
    print("check fk products->customers ok")
