import json
from collections.abc import Mapping
from decimal import Decimal

import psycopg
from psycopg.types.json import set_json_dumps, set_json_loads


# json.dumps cannot write a Decimal as a JSON number, and psycopg's loader reads every fraction as a float, so jsonb
# goes through this codec: amounts stay exact both ways, and a float refuses to be written at all.
def dumps_exact(value: object) -> str:
    if value is None or isinstance(value, bool):
        return json.dumps(value)
    if isinstance(value, int | str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, Decimal):
        return exact_number(value)
    if isinstance(value, Mapping):
        return "{" + ",".join(f"{dumps_key(key)}:{dumps_exact(item)}" for key, item in value.items()) + "}"
    if isinstance(value, list | tuple):
        return "[" + ",".join(dumps_exact(item) for item in value) + "]"
    raise TypeError(f"{type(value).__name__} is not stored as JSON")


def exact_number(value: Decimal) -> str:
    if not value.is_finite():
        raise ValueError(f"{value} is not a JSON number")
    return format(value, "f")


def dumps_key(key: object) -> str:
    if not isinstance(key, str):
        raise TypeError(f"a JSON key is text, got {type(key).__name__}")
    return json.dumps(key, ensure_ascii=False)


def loads_exact(raw: str | bytes) -> object:
    return json.loads(raw, parse_float=Decimal)


def configure_json(conn: psycopg.Connection) -> None:
    set_json_dumps(dumps_exact, conn)
    set_json_loads(loads_exact, conn)
