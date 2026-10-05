import re
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

from pipeline.bronze import aws_s3_copy, download_if_missing, ensure_bronze, run_command

SOURCE_KEYS = [
    "data/customers.csv",
    "data/products.csv",
    "data/daily_exchange_rates.csv",
    "data/service_agents.csv",
]
SOURCE_NAMES = ["customers.csv", "products.csv", "daily_exchange_rates.csv", "service_agents.csv"]


class RecordingCopier:
    def __init__(self) -> None:
        self.keys: list[str] = []

    def __call__(self, key: str, dest: Path) -> None:
        self.keys.append(key)
        dest.write_text("header\nrow\n", encoding="utf-8")


def refuse_copy(key: str, dest: Path) -> None:
    raise AssertionError(f"copied {key} although {dest.name} is on disk")


def copy_nothing(key: str, dest: Path) -> None:
    return None


def set_aws_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-key-id")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-2")
    monkeypatch.setenv("S3_BUCKET", "my-bucket")


def clear_aws_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_DEFAULT_REGION", "S3_BUCKET"):
        monkeypatch.delenv(name, raising=False)


def test_download_fails_loud_without_aws_and_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_aws_variables(monkeypatch)
    dest = tmp_path / "customers.csv"
    with pytest.raises(SystemExit, match="AWS_ACCESS_KEY_ID"):
        download_if_missing("data/customers.csv", dest, refuse_copy)


def test_the_first_start_copies_only_the_four_source_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    set_aws_variables(monkeypatch)
    copier = RecordingCopier()
    root = tmp_path / "raw"

    files = ensure_bronze(root, copier)

    assert copier.keys == SOURCE_KEYS
    assert [item.relative_name for item in files] == SOURCE_NAMES
    assert sorted(path.name for path in root.iterdir()) == sorted(SOURCE_NAMES)


def test_files_already_on_disk_are_not_copied_again(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clear_aws_variables(monkeypatch)
    for name in SOURCE_NAMES:
        (tmp_path / name).write_text("header\nrow\n", encoding="utf-8")

    files = ensure_bronze(tmp_path, refuse_copy)

    assert [item.relative_name for item in files] == SOURCE_NAMES


def test_an_empty_file_on_disk_is_copied_again(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    set_aws_variables(monkeypatch)
    for name in SOURCE_NAMES:
        (tmp_path / name).write_text("header\nrow\n", encoding="utf-8")
    (tmp_path / "products.csv").write_bytes(b"")
    copier = RecordingCopier()

    ensure_bronze(tmp_path, copier)

    assert copier.keys == ["data/products.csv"]


def test_a_copy_that_writes_no_file_stops_the_load(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    set_aws_variables(monkeypatch)
    expected = f"Bronze file missing or empty after download: {tmp_path / 'customers.csv'}"
    with pytest.raises(SystemExit, match=f"^{re.escape(expected)}$"):
        ensure_bronze(tmp_path, copy_nothing)


def test_the_aws_copy_reads_one_key_from_the_bucket(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    set_aws_variables(monkeypatch)
    monkeypatch.setenv("S3_BUCKET", "my-bucket/data")
    calls: list[tuple[list[str], str]] = []

    def record(argv: Sequence[str], failure: str) -> None:
        calls.append((list(argv), failure))

    dest = tmp_path / "customers.csv"
    aws_s3_copy("data/customers.csv", dest, record)

    assert calls == [
        (
            ["aws", "s3", "cp", "s3://my-bucket/data/customers.csv", str(dest), "--region", "us-east-2"],
            "aws s3 cp failed for key=data/customers.csv",
        )
    ]


def test_a_command_that_succeeds_returns() -> None:
    run_command([sys.executable, "-c", "pass"], "never shown")


def test_a_command_that_fails_stops_the_load_with_its_error() -> None:
    script = "import sys; sys.stderr.write('access denied'); sys.exit(3)"
    with pytest.raises(SystemExit, match=f"^{re.escape('aws s3 cp failed for key=data/products.csv: access denied')}$"):
        run_command([sys.executable, "-c", script], "aws s3 cp failed for key=data/products.csv")


def test_a_failed_command_with_no_stderr_reports_its_stdout() -> None:
    script = "import sys; print('no such bucket'); sys.exit(1)"
    with pytest.raises(SystemExit, match=f"^{re.escape('copy failed: no such bucket')}$"):
        run_command([sys.executable, "-c", script], "copy failed")
