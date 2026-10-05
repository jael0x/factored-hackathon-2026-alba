from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import TypeAlias

JsonValue: TypeAlias = "str | int | Decimal | bool | None | Sequence[JsonValue] | Mapping[str, JsonValue]"
Payload = Mapping[str, JsonValue]
