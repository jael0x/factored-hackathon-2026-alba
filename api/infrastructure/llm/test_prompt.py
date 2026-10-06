from typing import get_args
from uuid import UUID

from api.application.cycle.ports import TurnRequest
from api.contract_models import ProductKey
from api.infrastructure.llm.prompt import (
    CATALOG_ORDER,
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    catalog,
    turn_schema,
    user_message,
)

FIELDS = [
    "intent",
    "product",
    "declared_income_amount",
    "declared_income_currency",
    "language",
    "needs_clarification",
    "clarification_question",
    "reply_text",
]


def keys_of(node: object) -> set[str]:
    if isinstance(node, dict):
        return set(node) | {key for value in node.values() for key in keys_of(value)}
    if isinstance(node, list):
        return {key for item in node for key in keys_of(item)}
    return set()


def test_the_catalog_names_both_products_in_a_fixed_order() -> None:
    assert catalog() == (
        '- credit_card: es "una tarjeta de crédito", pt "um cartão de crédito"\n'
        '- personal_loan: es "un préstamo personal", pt "um empréstimo pessoal"'
    )
    assert set(CATALOG_ORDER) == set(get_args(ProductKey))
    assert catalog() in SYSTEM_PROMPT


def test_the_schema_is_the_turn_without_the_keywords_claude_does_not_accept() -> None:
    schema = turn_schema()
    assert (schema["required"], schema["additionalProperties"]) == (FIELDS, False)
    assert keys_of(schema) & {"minimum", "title"} == set()


def test_the_prompt_carries_no_identifier_of_the_case() -> None:
    request = TurnRequest(
        UUID("11111111-1111-4111-8111-111111111111"),
        UUID("33333333-3333-4333-8333-333333333333"),
        "hola",
        "pt",
        "ai_active",
        False,
        True,
        True,
        False,
    )
    text = user_message(request)
    assert "11111111" not in text and "33333333" not in text
    assert text == (
        "Reply language: pt\nCase state: ai_active\n"
        "On file: income no, credit score yes, active credit card yes, active personal loan no\n"
        "<message>\nhola\n</message>"
    )
    assert PROMPT_VERSION == "alba-turn-v1"
