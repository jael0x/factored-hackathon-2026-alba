from collections.abc import Mapping, Sequence
from decimal import Decimal

type JsonValue = str | int | Decimal | bool | None | Sequence[JsonValue] | Mapping[str, JsonValue]
Payload = Mapping[str, JsonValue]
