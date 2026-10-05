import json
from decimal import Decimal

import pytest
from pydantic import ValidationError

from api.infrastructure.llm.schema import ConversationTurn, InvalidConversationTurn, parse_conversation_turn

FIELDS: dict[str, object] = {
    "intent": "clarify",
    "product": None,
    "declared_income_currency": None,
    "language": "es",
    "needs_clarification": True,
    "clarification_question": "¿Tarjeta de crédito o préstamo personal?",
    "reply_text": "¿Te interesa una tarjeta de crédito o un préstamo personal?",
}


def turn_json(amount: str = "null", without: str | None = None, **overrides: object) -> str:
    fields = {name: value for name, value in {**FIELDS, **overrides}.items() if name != without}
    members = [f"{json.dumps(name)}: {json.dumps(value)}" for name, value in fields.items()]
    if without != "declared_income_amount":
        members.append(f'"declared_income_amount": {amount}')
    return "{" + ", ".join(members) + "}"


def test_a_turn_parses_to_its_full_value() -> None:
    raw = turn_json(
        amount="45000",
        intent="provide_income",
        declared_income_currency="MXN",
        needs_clarification=False,
        clarification_question=None,
        reply_text="Gracias, ya tengo el dato.",
    )
    assert parse_conversation_turn(raw) == ConversationTurn(
        intent="provide_income",
        product=None,
        declared_income_amount=Decimal("45000"),
        declared_income_currency="MXN",
        language="es",
        needs_clarification=False,
        clarification_question=None,
        reply_text="Gracias, ya tengo el dato.",
    )


def test_bytes_and_text_parse_the_same() -> None:
    raw = turn_json(product="credit_card", intent="prequalify_card")
    assert parse_conversation_turn(raw.encode()) == parse_conversation_turn(raw)


@pytest.mark.parametrize(
    ("amount", "exact"),
    [
        ("0", "0"),
        ("0.1", "0.1"),
        ("45000", "45000"),
        ("45000.10", "45000.10"),
        ("12345678901234567890.123456789", "12345678901234567890.123456789"),
        ("1e400", "1E+400"),
    ],
)
def test_an_amount_is_read_as_the_exact_decimal_written(amount: str, exact: str) -> None:
    parsed = parse_conversation_turn(turn_json(amount=amount)).declared_income_amount
    assert type(parsed) is Decimal
    assert str(parsed) == exact


REFUSED: list[tuple[str, str | bytes]] = [
    ("a missing field", turn_json(without="reply_text")),
    ("a missing amount", turn_json(without="declared_income_amount")),
    ("a field the contract does not name", turn_json(confidence=0.9)),
    ("English, which D22 removed", turn_json(language="en")),
    ("an unknown intent", turn_json(intent="apply_mortgage")),
    ("a product outside the catalog", turn_json(product="mortgage")),
    ("a currency the load does not carry", turn_json(declared_income_currency="USD")),
    ("an amount written as text", turn_json(amount='"45000"')),
    ("an amount written as a boolean", turn_json(amount="true")),
    ("a negative amount", turn_json(amount="-1")),
    ("NaN", turn_json(amount="NaN")),
    ("Infinity", turn_json(amount="Infinity")),
    ("a boolean written as text", turn_json(needs_clarification="false")),
    ("a null reply", turn_json(reply_text=None)),
    ("a repeated key", turn_json()[:-1] + ', "intent": "chit_chat"}'),
    ("a list instead of an object", "[]"),
    ("truncated JSON", turn_json()[:-1]),
    ("bytes that are not UTF-8", b"\xff"),
]


@pytest.mark.parametrize("raw", [case[1] for case in REFUSED], ids=[case[0] for case in REFUSED])
def test_output_outside_the_contract_shape_is_refused(raw: str | bytes) -> None:
    with pytest.raises(InvalidConversationTurn) as refused:
        parse_conversation_turn(raw)
    assert isinstance(refused.value.__cause__, ValueError)


def test_a_parsed_turn_cannot_be_changed() -> None:
    turn = parse_conversation_turn(turn_json())
    with pytest.raises(ValidationError):
        turn.intent = "chit_chat"  # type: ignore[misc]


def test_the_json_schema_is_the_contract_shape_with_every_field_required() -> None:
    nullable_enum = [{"type": "null"}]
    assert ConversationTurn.model_json_schema() == {
        "title": "ConversationTurn",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "intent",
            "product",
            "declared_income_amount",
            "declared_income_currency",
            "language",
            "needs_clarification",
            "clarification_question",
            "reply_text",
        ],
        "properties": {
            "intent": {
                "title": "Intent",
                "type": "string",
                "enum": [
                    "product_info",
                    "prequalify_card",
                    "prequalify_loan",
                    "confirm_prequalify",
                    "decline_prequalify",
                    "provide_income",
                    "human_request",
                    "out_of_scope",
                    "clarify",
                    "chit_chat",
                ],
            },
            "product": {
                "title": "Product",
                "anyOf": [{"type": "string", "enum": ["credit_card", "personal_loan"]}, *nullable_enum],
            },
            "declared_income_amount": {
                "title": "Declared Income Amount",
                "anyOf": [{"type": "number", "minimum": 0}, *nullable_enum],
            },
            "declared_income_currency": {
                "title": "Declared Income Currency",
                "anyOf": [{"type": "string", "enum": ["MXN", "COP", "ARS"]}, *nullable_enum],
            },
            "language": {"title": "Language", "type": "string", "enum": ["es", "pt", "other"]},
            "needs_clarification": {"title": "Needs Clarification", "type": "boolean"},
            "clarification_question": {
                "title": "Clarification Question",
                "anyOf": [{"type": "string"}, *nullable_enum],
            },
            "reply_text": {"title": "Reply Text", "type": "string"},
        },
    }
