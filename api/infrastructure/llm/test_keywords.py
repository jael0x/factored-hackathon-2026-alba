from decimal import Decimal
from typing import get_args

import pytest

from api.application.cycle.ports import TurnRequest
from api.contract_models import Locale
from api.domain.process.turns import ShownReading, TurnReading
from api.infrastructure.llm.keywords import read_keyword_turn
from api.tests.turn_harness import TurnFixtureName, load_turn_fixture

FIXTURES: tuple[TurnFixtureName, ...] = get_args(TurnFixtureName)
# The outcome phrases only a template writes (ARCHITECTURE.md, "Policy alba-credit-v1").
OUTCOME_PHRASES = ("precalifica", "no precalifica", "pré-qualificado", "não pré-qualifica")


def read(text: str, locale: Locale) -> TurnReading:
    request = TurnRequest(text, locale, "ai_active", True, True, False, False)
    reading = read_keyword_turn(request)
    assert isinstance(reading, ShownReading)
    return reading.reading


@pytest.mark.parametrize("name", FIXTURES)
def test_b0_labels_every_turn_fixture_as_the_model_does(name: TurnFixtureName) -> None:
    fixture = load_turn_fixture(name)
    turn = read(fixture.text, fixture.locale)
    expected = fixture.turn
    assert (
        turn.intent,
        turn.product,
        turn.language,
        turn.declared_income_amount,
        turn.declared_income_currency,
    ) == (
        expected.intent,
        expected.product,
        expected.language,
        expected.declared_income_amount,
        expected.declared_income_currency,
    )


@pytest.mark.parametrize(
    ("text", "locale", "reply"),
    [
        ("quiero un crédito", "es", "¿Te interesa una tarjeta de crédito o un préstamo personal?"),
        ("quiero un crédito", "pt", "Você tem interesse em um cartão de crédito ou em um empréstimo pessoal?"),
        ("quero um crédito", "es", "¿Te interesa una tarjeta de crédito o un préstamo personal?"),
    ],
)
def test_b0_replies_in_the_language_chosen_with_the_switch(text: str, locale: Locale, reply: str) -> None:
    assert read(text, locale).reply_text == reply


@pytest.mark.parametrize(
    ("text", "intent", "amount", "currency"),
    [
        ("gano 12.500 pesos mexicanos al mes", "provide_income", Decimal(12500), "MXN"),
        ("sí, gano 3,200,000 COP al mes", "confirm_prequalify", Decimal(3200000), "COP"),
        ("ganho 4500,50 por mês", "provide_income", Decimal("4500.50"), None),
    ],
)
def test_b0_reads_an_income_and_a_currency_that_names_the_country(
    text: str, intent: str, amount: Decimal, currency: str | None
) -> None:
    turn = read(text, "es")
    assert (turn.intent, turn.declared_income_amount, turn.declared_income_currency) == (intent, amount, currency)


@pytest.mark.parametrize("name", FIXTURES)
def test_b0_never_writes_an_outcome_phrase(name: TurnFixtureName) -> None:
    fixture = load_turn_fixture(name)
    locales: tuple[Locale, ...] = ("es", "pt")
    for locale in locales:
        reply = read(fixture.text, locale).reply_text.lower()
        assert not any(phrase in reply for phrase in OUTCOME_PHRASES)


@pytest.mark.parametrize(
    ("text", "locale", "intent", "language"),
    [
        ("hola", "es", "chit_chat", "es"),
        ("gano bien al mes", "es", "clarify", "es"),
        ("ok", "pt", "confirm_prequalify", "pt"),
        ("ok", "es", "confirm_prequalify", "es"),
    ],
    ids=["a greeting", "income words with no amount", "no language words, Portuguese chosen", "no language words"],
)
def test_b0_falls_back_to_the_switch_when_no_word_names_a_language(
    text: str, locale: Locale, intent: str, language: str
) -> None:
    turn = read(text, locale)
    assert (turn.intent, turn.language, turn.declared_income_amount) == (intent, language, None)
