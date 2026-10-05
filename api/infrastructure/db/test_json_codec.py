from decimal import Decimal

import pytest

from api.infrastructure.db.json_codec import dumps_exact, loads_exact


def test_an_amount_is_written_and_read_back_exactly() -> None:
    payload = {"amount": Decimal("45000.50"), "count": 2, "ok": True, "none": None, "text": "sí", "list": [Decimal(1)]}
    written = dumps_exact(payload)
    assert written == '{"amount":45000.50,"count":2,"ok":true,"none":null,"text":"sí","list":[1]}'
    read_back = loads_exact(written)
    assert read_back == payload
    assert isinstance(read_back, dict)
    assert type(read_back["amount"]) is Decimal


def test_a_tuple_is_written_as_a_list() -> None:
    assert dumps_exact((1, "a")) == '[1,"a"]'


def test_a_float_is_never_written() -> None:
    with pytest.raises(TypeError, match="float is not stored as JSON"):
        dumps_exact({"amount": 45000.5})


@pytest.mark.parametrize("amount", ["NaN", "Infinity", "-Infinity"])
def test_an_amount_that_is_not_a_number_is_refused(amount: str) -> None:
    with pytest.raises(ValueError, match="is not a JSON number"):
        dumps_exact(Decimal(amount))


def test_a_key_that_is_not_text_is_refused() -> None:
    with pytest.raises(TypeError, match="a JSON key is text, got int"):
        dumps_exact({1: "one"})
