from pathlib import Path

from pipeline.constants import EXPECTED_ROW_COUNTS, S3_KEYS
from pipeline.silver import TABLE_COLUMNS, TABLE_NAME


def test_the_snapshot_sizes_are_the_measured_ones() -> None:
    assert EXPECTED_ROW_COUNTS == {
        "customers.csv": 150_000,
        "products.csv": 400_000,
        "daily_exchange_rates.csv": 13_164,
        "service_agents.csv": 1_200,
    }


def test_every_source_file_has_a_size_a_table_and_columns() -> None:
    names = {Path(key).name for key in S3_KEYS}
    assert len(names) == len(S3_KEYS)
    assert set(EXPECTED_ROW_COUNTS) == names
    assert set(TABLE_NAME) == names
    assert set(TABLE_COLUMNS) == names
