import csv
from collections.abc import Iterable, Iterator, Mapping, Sequence
from pathlib import Path

from pipeline.bronze import BronzeFile
from pipeline.csv_header import require_columns

CUSTOMER_REPORT_COLUMNS = ("credit_score", "estimated_monthly_income")


def read_csv_rows(path: Path, columns: Sequence[str]) -> Iterator[dict[str, str | None]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        require_columns(path, reader.fieldnames, columns)
        yield from reader


def is_empty(value: str | None) -> bool:
    return (value or "").strip() == ""


def count_customer_nulls(rows: Iterable[Mapping[str, str | None]]) -> tuple[int, int, int]:
    total = null_score = null_income = 0
    for row in rows:
        total += 1
        null_score += is_empty(row["credit_score"])
        null_income += is_empty(row["estimated_monthly_income"])
    return total, null_score, null_income


def report_customer_nulls(customers_path: Path) -> tuple[int, int, int]:
    total, null_score, null_income = count_customer_nulls(read_csv_rows(customers_path, CUSTOMER_REPORT_COLUMNS))
    print(f"check nulls customers total={total} null_score={null_score} null_income={null_income}")
    return total, null_score, null_income


def report_load(files: Sequence[BronzeFile]) -> None:
    by_name = {item.relative_name: item for item in files}
    report_customer_nulls(by_name["customers.csv"].path)
