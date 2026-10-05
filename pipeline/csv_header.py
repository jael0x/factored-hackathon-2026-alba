from collections.abc import Sequence
from pathlib import Path


def require_columns(path: Path, fieldnames: Sequence[str] | None, columns: Sequence[str]) -> None:
    if fieldnames is None:
        raise SystemExit(f"CSV has no header: {path}")
    missing = [col for col in columns if col not in fieldnames]
    if missing:
        raise SystemExit(f"CSV {path.name} missing columns {missing}. Found={list(fieldnames)}")
