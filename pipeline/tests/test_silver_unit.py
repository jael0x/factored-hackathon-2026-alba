import pytest

from pipeline.silver import coerce_cell


def test_coerce_credit_score_float_string() -> None:
    assert coerce_cell("credit_score", "701.0") == 701


def test_coerce_days_past_due_int_string() -> None:
    assert coerce_cell("days_past_due", "180") == 180


def test_coerce_empty_to_none() -> None:
    assert coerce_cell("credit_score", "") is None
    assert coerce_cell("credit_score", "   ") is None
    assert coerce_cell("credit_score", None) is None


def test_an_empty_balance_loads_as_zero() -> None:
    assert coerce_cell("current_balance", "") == 0
    assert coerce_cell("current_balance", "   ") == 0
    assert coerce_cell("current_balance", None) == 0


def test_a_balance_keeps_its_value() -> None:
    assert coerce_cell("current_balance", "1559.57") == "1559.57"
    assert coerce_cell("current_balance", "0.0") == "0.0"


def test_only_the_balance_loads_empty_as_zero() -> None:
    assert coerce_cell("estimated_monthly_income", "") is None
    assert coerce_cell("days_past_due", "") is None


def test_coerce_non_integer_column_keeps_string() -> None:
    assert coerce_cell("customer_id", "CLI-1") == "CLI-1"


def test_coerce_invalid_integer_raises() -> None:
    with pytest.raises(ValueError):
        coerce_cell("credit_score", "not-a-number")
