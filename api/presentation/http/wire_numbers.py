from collections.abc import Mapping
from decimal import Decimal

type WireValue = str | int | float | bool | None | list[WireValue] | dict[str, WireValue]


# The wire carries amounts as JSON numbers, which clients read as doubles. A decimal is written only when the double
# prints back the same decimal, so no amount is rounded on its way out (ARCHITECTURE.md, "HTTP contract").
def wire_number(amount: Decimal) -> float:
    number = float(amount)
    if not amount.is_finite() or Decimal(repr(number)) != amount:
        raise ValueError(f"{amount} cannot be written as a JSON number without rounding")
    return number


def wire_optional_number(amount: Decimal | None) -> float | None:
    return None if amount is None else wire_number(amount)


def wire_json(value: object) -> WireValue:
    if value is None or isinstance(value, str | bool | int):
        return value
    if isinstance(value, Decimal):
        return wire_number(value)
    if isinstance(value, Mapping):
        return {require_key(key): wire_json(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [wire_json(item) for item in value]
    raise TypeError(f"{type(value).__name__} is not a stored JSON value")


def require_key(key: object) -> str:
    if not isinstance(key, str):
        raise TypeError(f"a JSON key must be text, got {key!r}")
    return key
