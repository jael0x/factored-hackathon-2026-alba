import json
from decimal import Decimal
from typing import Annotated, NoReturn

from pydantic import BaseModel, ConfigDict, Field, WithJsonSchema

from api.contract_models import IncomeCurrency, Intent, ProductKey, TurnLanguage
from api.domain.process.turns import TurnReading

IncomeAmount = Annotated[Decimal, Field(ge=0, allow_inf_nan=False), WithJsonSchema({"type": "number", "minimum": 0})]


class ConversationTurn(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    intent: Intent
    product: ProductKey | None
    declared_income_amount: IncomeAmount | None
    declared_income_currency: IncomeCurrency | None
    language: TurnLanguage
    needs_clarification: bool
    clarification_question: str | None
    reply_text: str


def reading_of(turn: ConversationTurn) -> TurnReading:
    return TurnReading(
        intent=turn.intent,
        product=turn.product,
        language=turn.language,
        declared_income_amount=turn.declared_income_amount,
        declared_income_currency=turn.declared_income_currency,
        reply_text=turn.reply_text,
    )


class InvalidConversationTurn(Exception):
    pass


def parse_conversation_turn(raw: str | bytes) -> ConversationTurn:
    try:
        return ConversationTurn.model_validate(decode_exact_json(raw))
    except ValueError as error:
        raise InvalidConversationTurn(str(error)) from error


# Pydantic's own JSON parser accepts a quoted amount and keeps the last of two equal keys, so the text is decoded
# here first: every number as an exact Decimal, and any repeated key refused.
def decode_exact_json(raw: str | bytes) -> object:
    return json.loads(
        raw,
        parse_float=Decimal,
        parse_int=Decimal,
        parse_constant=refuse_constant,
        object_pairs_hook=refuse_repeated_keys,
    )


def refuse_constant(name: str) -> NoReturn:
    raise ValueError(f"{name} is not a JSON number")


def refuse_repeated_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    keys = [key for key, _ in pairs]
    repeated = sorted({key for key in keys if keys.count(key) > 1})
    if repeated:
        raise ValueError(f"repeated keys: {', '.join(repeated)}")
    return dict(pairs)
