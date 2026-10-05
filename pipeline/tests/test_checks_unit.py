import re
from pathlib import Path

import pytest

from pipeline.bronze import BronzeFile, file_sha256
from pipeline.checks import (
    assert_expected_row_counts,
    count_csv_rows,
    report_customer_nulls,
)


def _bronze(path: Path) -> BronzeFile:
    return BronzeFile(
        relative_name=path.name,
        path=path,
        bytes=path.stat().st_size,
        sha256=file_sha256(path),
    )


def test_count_csv_rows(testdata_dir: Path) -> None:
    assert count_csv_rows(testdata_dir / "customers.csv") == 3
    assert count_csv_rows(testdata_dir / "products.csv") == 2
    assert count_csv_rows(testdata_dir / "service_agents.csv") == 1


def test_assert_expected_row_counts_ok(testdata_dir: Path) -> None:
    files = [
        _bronze(testdata_dir / "customers.csv"),
        _bronze(testdata_dir / "products.csv"),
        _bronze(testdata_dir / "service_agents.csv"),
    ]
    assert_expected_row_counts(
        files,
        {
            "customers.csv": 3,
            "products.csv": 2,
            "service_agents.csv": 1,
        },
    )


def test_assert_expected_row_counts_fails_on_mismatch(testdata_dir: Path) -> None:
    files = [_bronze(testdata_dir / "customers.csv")]
    with pytest.raises(SystemExit, match="expected 150000 rows, got 3"):
        assert_expected_row_counts(files, {"customers.csv": 150_000})


def test_assert_expected_row_counts_fails_when_missing(testdata_dir: Path) -> None:
    files = [_bronze(testdata_dir / "customers.csv")]
    with pytest.raises(SystemExit, match=re.escape("missing bronze file products.csv")):
        assert_expected_row_counts(files, {"products.csv": 2})


def test_report_customer_nulls(testdata_dir: Path) -> None:
    total, null_score, null_income = report_customer_nulls(testdata_dir / "customers.csv")
    assert total == 3
    assert null_score == 1
    assert null_income == 1


def test_a_bronze_file_with_no_expected_row_count_stops_the_load(testdata_dir: Path) -> None:
    files = [_bronze(testdata_dir / "customers.csv"), _bronze(testdata_dir / "daily_exchange_rates.csv")]
    with pytest.raises(
        SystemExit, match=f"^{re.escape('Quality check: no expected row count for daily_exchange_rates.csv')}$"
    ):
        assert_expected_row_counts(files, {"customers.csv": 3})


@pytest.mark.parametrize(
    "name",
    ["customers.csv", "products.csv", "daily_exchange_rates.csv", "service_agents.csv"],
)
def test_one_row_fewer_than_the_snapshot_stops_the_load(name: str, testdata_dir: Path, tmp_path: Path) -> None:
    for source in testdata_dir.iterdir():
        (tmp_path / source.name).write_bytes(source.read_bytes())
    lines = (tmp_path / name).read_text(encoding="utf-8-sig").splitlines(keepends=True)
    (tmp_path / name).write_text("".join(lines[:-1]), encoding="utf-8")
    expected = {"customers.csv": 3, "products.csv": 2, "daily_exchange_rates.csv": 3, "service_agents.csv": 1}
    files = [_bronze(tmp_path / source) for source in expected]
    message = f"^Quality check failed for {re.escape(name)}: expected {expected[name]} rows, got {expected[name] - 1}$"
    with pytest.raises(SystemExit, match=message):
        assert_expected_row_counts(files, expected)
