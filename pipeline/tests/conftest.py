from pathlib import Path

import pytest

TESTDATA = Path(__file__).resolve().parents[1] / "testdata"


@pytest.fixture
def testdata_dir() -> Path:
    return TESTDATA
