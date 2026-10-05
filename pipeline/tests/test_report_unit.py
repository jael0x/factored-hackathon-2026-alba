import itertools
import re
from pathlib import Path

import pytest

from pipeline.bronze import BronzeFile, file_sha256
from pipeline.report import count_active_products_by_type, report_active_products, report_customer_nulls, report_load

PRODUCT_ROWS = [
    {"product_type": "Tarjeta Crédito", "product_status": "Active"},
    {"product_type": "Cuenta Ahorro", "product_status": "Active"},
    {"product_type": "Tarjeta Crédito", "product_status": "Active"},
    {"product_type": "Préstamo Personal", "product_status": "Blocked"},
    {"product_type": "Seguro", "product_status": "Suspended"},
    {"product_type": "Cuenta Ahorro", "product_status": "Closed"},
    {"product_type": "Préstamo Hipotecario", "product_status": " Active "},
]


def _bronze(path: Path) -> BronzeFile:
    return BronzeFile(relative_name=path.name, path=path, bytes=path.stat().st_size, sha256=file_sha256(path))


def test_the_load_report_counts_the_customers_without_a_score(testdata_dir: Path) -> None:
    assert report_customer_nulls(testdata_dir / "customers.csv") == (3, 1, 1)


def test_only_active_products_are_counted_by_type_in_name_order() -> None:
    counts = count_active_products_by_type(PRODUCT_ROWS)
    assert list(counts.items()) == [
        ("Cuenta Ahorro", 1),
        ("Préstamo Hipotecario", 1),
        ("Tarjeta Crédito", 2),
    ]


def test_the_row_order_does_not_change_the_report() -> None:
    expected = list(count_active_products_by_type(PRODUCT_ROWS).items())
    reports = {
        tuple(count_active_products_by_type(order).items()) for order in itertools.permutations(PRODUCT_ROWS[:5])
    }
    assert reports == {(("Cuenta Ahorro", 1), ("Tarjeta Crédito", 2))}
    assert list(count_active_products_by_type(reversed(PRODUCT_ROWS)).items()) == expected


def test_no_active_product_reports_nothing() -> None:
    assert count_active_products_by_type([{"product_type": "Seguro", "product_status": "Closed"}]) == {}


def test_the_load_report_prints_each_count(testdata_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    files = [_bronze(testdata_dir / name) for name in ("customers.csv", "products.csv")]
    report_load(files)
    assert capsys.readouterr().out.splitlines() == [
        "check nulls customers total=3 null_score=1 null_income=1",
        "report active products type=Préstamo Hipotecario count=1",
        "report active products type=Tarjeta Crédito count=1",
        "report active products total=2",
    ]


@pytest.mark.parametrize(
    ("header", "missing"),
    [
        ("product_id,customer_id,product_type", "['product_status']"),
        ("product_id,customer_id,product_status", "['product_type']"),
    ],
)
def test_a_report_column_missing_from_its_file_stops_the_load(header: str, missing: str, tmp_path: Path) -> None:
    path = tmp_path / "products.csv"
    path.write_text(f"{header}\nPRD-1,CLI-1,Active\n", encoding="utf-8")
    expected = f"CSV products.csv missing columns {missing}. Found={header.split(',')}"
    with pytest.raises(SystemExit, match=f"^{re.escape(expected)}$"):
        report_active_products(path)


def test_a_customers_file_without_the_income_column_stops_the_load(tmp_path: Path) -> None:
    path = tmp_path / "customers.csv"
    path.write_text("customer_id,credit_score\nCLI-1,\n", encoding="utf-8")
    with pytest.raises(SystemExit, match=re.escape("missing columns ['estimated_monthly_income']")):
        report_customer_nulls(path)


def test_an_empty_file_has_no_header(tmp_path: Path) -> None:
    path = tmp_path / "products.csv"
    path.write_text("", encoding="utf-8")
    with pytest.raises(SystemExit, match=f"^CSV has no header: {re.escape(str(path))}$"):
        report_active_products(path)
