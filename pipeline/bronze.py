import hashlib
import os
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from pipeline.constants import S3_KEYS


@dataclass(frozen=True)
class BronzeFile:
    relative_name: str
    path: Path
    bytes: int
    sha256: str


type CopyObject = Callable[[str, Path], None]
type RunCommand = Callable[[Sequence[str], str], None]


def raw_dir() -> Path:
    return Path(os.environ.get("RAW_DIR", "data/raw"))


def bucket_name() -> str:
    raw = os.environ.get("S3_BUCKET", "").strip().rstrip("/")
    if not raw:
        raise SystemExit("S3_BUCKET is missing")
    if "/" not in raw:
        return raw
    bucket, rest = raw.split("/", 1)
    if rest == "data":
        print("S3_BUCKET had a /data suffix; using the bucket name only")
        return bucket
    raise SystemExit(
        "S3_BUCKET must be the bucket name only (optional trailing /data is stripped). "
        f"Got an unsupported path suffix (bucket_len={len(bucket)}, rest_len={len(rest)})."
    )


def aws_credentials_present() -> bool:
    return bool(
        os.environ.get("AWS_ACCESS_KEY_ID")
        and os.environ.get("AWS_SECRET_ACCESS_KEY")
        and os.environ.get("AWS_DEFAULT_REGION")
        and os.environ.get("S3_BUCKET")
    )


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_command(argv: Sequence[str], failure: str) -> None:
    result = subprocess.run(list(argv), capture_output=True, text=True, check=False)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise SystemExit(f"{failure}: {detail}")


def aws_s3_copy(key: str, dest: Path, run: RunCommand = run_command) -> None:
    region = os.environ["AWS_DEFAULT_REGION"]
    command = ["aws", "s3", "cp", f"s3://{bucket_name()}/{key}", str(dest), "--region", region]
    run(command, f"aws s3 cp failed for key={key}")


def download_if_missing(key: str, dest: Path, copy: CopyObject) -> None:
    if dest.is_file() and dest.stat().st_size > 0:
        return
    if not aws_credentials_present():
        raise SystemExit(
            f"Missing local file {dest} and AWS credentials are incomplete. "
            "Need AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION, S3_BUCKET."
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {key} ...")
    copy(key, dest)


def fetch_bronze_file(key: str, root: Path, copy: CopyObject) -> BronzeFile:
    name = Path(key).name
    dest = root / name
    download_if_missing(key, dest, copy)
    if not dest.is_file() or dest.stat().st_size == 0:
        raise SystemExit(f"Bronze file missing or empty after download: {dest}")
    item = BronzeFile(relative_name=name, path=dest, bytes=dest.stat().st_size, sha256=file_sha256(dest))
    print(f"bronze ok path={name} bytes={item.bytes} sha256={item.sha256[:12]}...")
    return item


def ensure_bronze(root: Path, copy: CopyObject) -> list[BronzeFile]:
    root.mkdir(parents=True, exist_ok=True)
    return [fetch_bronze_file(key, root, copy) for key in S3_KEYS]
