import pytest

from pipeline.bronze import bucket_name


def test_bucket_name_plain(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("S3_BUCKET", "my-bucket")
    assert bucket_name() == "my-bucket"


def test_bucket_name_strips_data_suffix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("S3_BUCKET", "my-bucket/data")
    assert bucket_name() == "my-bucket"


def test_bucket_name_strips_trailing_slash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("S3_BUCKET", "my-bucket/data/")
    assert bucket_name() == "my-bucket"


def test_bucket_name_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("S3_BUCKET", raising=False)
    with pytest.raises(SystemExit, match="S3_BUCKET is missing"):
        bucket_name()


def test_bucket_name_unsupported_suffix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("S3_BUCKET", "my-bucket/raw")
    with pytest.raises(SystemExit, match="unsupported path suffix"):
        bucket_name()
