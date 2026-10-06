from decimal import Decimal

import pytest

from api.presentation.http.wire_numbers import wire_json, wire_number, wire_optional_number


@pytest.mark.parametrize(
    ("amount", "number"),
    [
        (Decimal("4707334.28"), 4707334.28),
        (Decimal("17988.33"), 17988.33),
        (Decimal("0"), 0.0),
        (Decimal("306753.450"), 306753.45),
        (Decimal("999999999999999"), 999999999999999.0),
    ],
)
def test_an_amount_a_double_holds_is_written_as_that_number(amount: Decimal, number: float) -> None:
    written = wire_number(amount)
    assert (written, type(written)) == (number, float)


@pytest.mark.parametrize("amount", [Decimal("1234567890123456.78"), Decimal("0.1000000000000000055511151231257827")])
def test_an_amount_a_double_would_round_fails_loud(amount: Decimal) -> None:
    with pytest.raises(ValueError, match="cannot be written as a JSON number without rounding"):
        wire_number(amount)


@pytest.mark.parametrize("amount", [Decimal("Infinity"), Decimal("-Infinity"), Decimal("NaN")])
def test_a_number_json_cannot_hold_fails_loud(amount: Decimal) -> None:
    with pytest.raises(ValueError, match="cannot be written as a JSON number"):
        wire_number(amount)


def test_an_empty_amount_stays_empty() -> None:
    assert wire_optional_number(None) is None


def test_every_decimal_inside_a_payload_becomes_a_number_and_nothing_else_changes() -> None:
    payload = {
        "outcome": "REFER",
        "reply_ok": True,
        "product_asked_count": 0,
        "declared_income_amount": None,
        "rule_trace": [{"rule_id": "R05", "input": {"credit_score": 615, "income_local": Decimal("4707334.28")}}],
        "facts": [{"name": "income_usd", "value": Decimal("1167.42")}],
    }
    assert wire_json(payload) == {
        "outcome": "REFER",
        "reply_ok": True,
        "product_asked_count": 0,
        "declared_income_amount": None,
        "rule_trace": [{"rule_id": "R05", "input": {"credit_score": 615, "income_local": 4707334.28}}],
        "facts": [{"name": "income_usd", "value": 1167.42}],
    }


def test_a_boolean_is_not_read_as_a_whole_number() -> None:
    written = wire_json({"income_requested": False})
    assert written == {"income_requested": False}
    assert isinstance(written, dict)
    assert written["income_requested"] is False


@pytest.mark.parametrize("value", [1.5, b"bytes", object()])
def test_a_value_that_is_not_stored_json_fails_loud(value: object) -> None:
    with pytest.raises(TypeError, match="is not a stored JSON value"):
        wire_json({"value": value})


def test_a_key_that_is_not_text_fails_loud() -> None:
    with pytest.raises(TypeError, match="a JSON key must be text"):
        wire_json({1: "x"})
