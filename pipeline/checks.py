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
    missing = sorted(expected.keys() - by_name.keys())
    if missing:
        raise SystemExit(f"Quality check: missing bronze file {', '.join(missing)}")
    unexpected = sorted(by_name.keys() - expected.keys())
    if unexpected:
        raise SystemExit(f"Quality check: no expected row count for {', '.join(unexpected)}")
    for name, expected_count in expected.items():
        actual = count_csv_rows(by_name[name].path)
        if actual != expected_count:
            raise SystemExit(f"Quality check failed for {name}: expected {expected_count} rows, got {actual}")
        print(f"check rows ok {name}={actual}")


def run_bronze_checks(files: list[BronzeFile]) -> None:
    assert_expected_row_counts(files, EXPECTED_ROW_COUNTS)
