from decimal import Decimal

import pytest

from api.infrastructure.db.cases import amount, facts_by_name


def test_an_analysis_without_facts_names_none() -> None:
    assert facts_by_name(None) == {}


def test_facts_are_read_by_name() -> None:
    assert facts_by_name([{"name": "income_local", "value": 1}]) == {
        "income_local": {"name": "income_local", "value": 1}
    }


@pytest.mark.parametrize(("value", "read"), [(None, None), (45000, Decimal(45000)), (Decimal("1.5"), Decimal("1.5"))])
def test_an_income_fact_is_read_exactly(value: object, read: Decimal | None) -> None:
    assert amount(value) == read


@pytest.mark.parametrize("value", ["45000", True, 1.5])
def test_an_income_fact_that_is_not_an_exact_number_is_refused(value: object) -> None:
    with pytest.raises(TypeError, match="an income fact is a number"):
        amount(value)
