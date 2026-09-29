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
    with pytest.raises(SystemExit, match="missing bronze file products.csv"):
        assert_expected_row_counts(files, {"products.csv": 2})


def test_report_customer_nulls(testdata_dir: Path) -> None:
    total, null_score, null_income = report_customer_nulls(testdata_dir / "customers.csv")
    assert total == 3
    assert null_score == 1
    assert null_income == 1
