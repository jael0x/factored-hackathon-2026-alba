import re
from pathlib import Path

import pytest

from pipeline.report import report_customer_nulls


def test_the_load_report_counts_the_customers_without_a_score(testdata_dir: Path) -> None:
    assert report_customer_nulls(testdata_dir / "customers.csv") == (3, 1, 1)


def test_a_customers_file_without_the_income_column_stops_the_load(tmp_path: Path) -> None:
    path = tmp_path / "customers.csv"
    path.write_text("customer_id,credit_score\nCLI-1,\n", encoding="utf-8")
    with pytest.raises(SystemExit, match=re.escape("missing columns ['estimated_monthly_income']")):
        report_customer_nulls(path)


def test_an_empty_customers_file_has_no_header(tmp_path: Path) -> None:
    path = tmp_path / "customers.csv"
    path.write_text("", encoding="utf-8")
    with pytest.raises(SystemExit, match=f"^CSV has no header: {re.escape(str(path))}$"):
        report_customer_nulls(path)
