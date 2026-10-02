import csv
from pathlib import Path

from pipeline.bronze import BronzeFile
from pipeline.constants import EXPECTED_ROW_COUNTS


def count_csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        if header is None:
            return 0
        return sum(1 for _ in reader)


def assert_expected_row_counts(
    files: list[BronzeFile],
    expected: dict[str, int],
) -> None:
    by_name = {item.relative_name: item for item in files}
    for name, expected_count in expected.items():
        item = by_name.get(name)
        if item is None:
            raise SystemExit(f"Quality check: missing bronze file {name}")
        actual = count_csv_rows(item.path)
        if actual != expected_count:
            raise SystemExit(f"Quality check failed for {name}: expected {expected_count} rows, got {actual}")
        print(f"check rows ok {name}={actual}")


def report_customer_nulls(customers_path: Path) -> tuple[int, int, int]:
    null_score = 0
    null_income = 0
    total = 0
    with customers_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            total += 1
            if (row.get("credit_score") or "").strip() == "":
                null_score += 1
            if (row.get("estimated_monthly_income") or "").strip() == "":
                null_income += 1
    print(f"check nulls customers total={total} null_score={null_score} null_income={null_income}")
    return total, null_score, null_income


def run_bronze_checks(files: list[BronzeFile]) -> None:
    assert_expected_row_counts(files, EXPECTED_ROW_COUNTS)
    by_name = {item.relative_name: item for item in files}
    report_customer_nulls(by_name["customers.csv"].path)
