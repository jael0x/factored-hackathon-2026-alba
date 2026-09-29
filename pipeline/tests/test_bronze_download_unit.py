from pathlib import Path

import pytest

from pipeline.bronze import download_if_missing


def test_download_fails_loud_without_aws_and_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)
    monkeypatch.delenv("S3_BUCKET", raising=False)
    dest = tmp_path / "customers.csv"
    with pytest.raises(SystemExit, match="AWS_ACCESS_KEY_ID"):
        download_if_missing("data/customers.csv", dest)
