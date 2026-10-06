import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from api.tests.oracle import ORACLE_PATH, load_oracle


def fixture_with(tmp_path: Path, change: Any) -> Path:
    document = json.loads(ORACLE_PATH.read_text(encoding="utf-8"))
    change(document)
    path = tmp_path / "oracle.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_the_fixture_keeps_amounts_exact() -> None:
    [juan, *_] = load_oracle().customers
    assert str(juan.income_usd) == "17988.32906145"


def test_a_field_the_fixture_does_not_define_is_refused(tmp_path: Path) -> None:
    path = fixture_with(tmp_path, lambda d: d["customers"][0].update(document_number="60084840"))
    with pytest.raises(ValidationError, match="document_number"):
        load_oracle(path)


def test_a_quoted_amount_is_refused(tmp_path: Path) -> None:
    path = fixture_with(tmp_path, lambda d: d["customers"][0].update(income_local="306753.45"))
    with pytest.raises(ValidationError, match="income_local"):
        load_oracle(path)


def test_an_outcome_outside_the_closed_set_is_refused(tmp_path: Path) -> None:
    path = fixture_with(tmp_path, lambda d: d["customers"][0]["expected"].update(outcome="APPROVED"))
    with pytest.raises(ValidationError, match="outcome"):
        load_oracle(path)


def test_a_repeated_key_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "oracle.json"
    path.write_text('{"as_of": "2026-06-17", "as_of": "2026-06-18"}', encoding="utf-8")
    with pytest.raises(ValueError, match="repeated keys: as_of"):
        load_oracle(path)
