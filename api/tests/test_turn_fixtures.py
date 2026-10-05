from decimal import Decimal
from typing import get_args

import pytest

from api.domain.process.commands import SHOW_REPLY_COMMAND, Command, hand_off, run_policy, send_template
from api.domain.process.rules import ProcessRuleId, match_rules
from api.tests.turn_harness import (
    TURN_FIXTURES,
    Stamp,
    TurnFixtureName,
    classified_turn,
    load_turn_fixture,
)

Fired = tuple[tuple[ProcessRuleId, Command], ...]

FIXTURE_NAMES: tuple[TurnFixtureName, ...] = get_args(TurnFixtureName)

ASK_CONSENT: Fired = (("ask_confirm_prequalify", send_template("confirm_prequalify")),)
ASK_WHICH_PRODUCT: Fired = (("ask_which_product", send_template("which_product")),)
CLARIFY: Fired = (("show_reply", SHOW_REPLY_COMMAND),)
NO_PRODUCT_HANDOFF: Fired = (("hand_off_no_product", hand_off("out_of_scope")),)
LANGUAGE_HANDOFF: Fired = (("hand_off_language", hand_off("language_unsupported")),)

STEPS: list[tuple[str, TurnFixtureName, Stamp, Fired]] = [
    (
        "Juan, Juliana, Alicia, 04, 09: a card request asks for consent",
        "es-quiero-una-tarjeta-de-credito",
        Stamp("credit_card"),
        ASK_CONSENT,
    ),
    (
        "Juan, Juliana, Alicia, 05, 06, 07: a yes takes the stored card to the policy",
        "es-si",
        Stamp("credit_card"),
        (("run_policy", run_policy("credit_card", None, None)),),
    ),
    (
        "Juliana, 06: the income she was asked for runs the policy in her profile's currency",
        "es-gano-45000-pesos",
        Stamp("credit_card", income_requested=True),
        (("run_policy_income", run_policy("credit_card", Decimal("45000"), None)),),
    ),
    (
        "Mariana, 05: a loan request asks for consent",
        "es-quiero-un-prestamo-personal",
        Stamp("personal_loan"),
        ASK_CONSENT,
    ),
    (
        "Mariana: a yes takes the stored loan to the policy",
        "es-si",
        Stamp("personal_loan"),
        (("run_policy", run_policy("personal_loan", None, None)),),
    ),
    (
        "Juan in Portuguese, 12: a card request asks for consent",
        "pt-cartao-de-credito",
        Stamp("credit_card"),
        ASK_CONSENT,
    ),
    (
        "Juan in Portuguese, 05: a yes takes the stored card to the policy",
        "pt-sim",
        Stamp("credit_card"),
        (("run_policy", run_policy("credit_card", None, None)),),
    ),
    ("03, 12: a request with no product is clarified", "es-quiero-un-credito", Stamp(None), CLARIFY),
    (
        "03: naming the card after the question asks for consent",
        "es-una-tarjeta-de-credito",
        Stamp("credit_card", product_asked_count=1),
        ASK_CONSENT,
    ),
    (
        "03: a second request with no product is asked again",
        "es-el-credito",
        Stamp(None, product_asked_count=1),
        CLARIFY,
    ),
    (
        "03: a third request with no product goes to a person",
        "es-el-credito",
        Stamp(None, product_asked_count=2),
        NO_PRODUCT_HANDOFF,
    ),
    (
        "03: a yes with no product after two questions goes to a person",
        "es-si",
        Stamp(None, product_asked_count=2),
        NO_PRODUCT_HANDOFF,
    ),
    ("03: a question about the products gets a reply", "es-que-productos-ofrecen", Stamp(None), CLARIFY),
    (
        "04: declining shows the reply",
        "es-no-gracias",
        Stamp("credit_card"),
        (("decline_prequalify", SHOW_REPLY_COMMAND),),
    ),
    (
        "04: a new request after a decline asks again",
        "es-mejor-si-quiero-la-tarjeta",
        Stamp("credit_card"),
        ASK_CONSENT,
    ),
    (
        "04: an income instead of the consent answer asks for consent again",
        "es-gano-45000-pesos",
        Stamp("credit_card"),
        (("ask_consent_for_income", send_template("confirm_prequalify")),),
    ),
    (
        "04: a yes that states an income runs the policy with it",
        "es-si-gano-45000-pesos",
        Stamp("credit_card"),
        (("run_policy", run_policy("credit_card", Decimal("45000"), None)),),
    ),
    ("04: a yes that names no product is asked which", "es-si-quiero-precalificar", Stamp(None), ASK_WHICH_PRODUCT),
    ("06: an income before any product is asked which", "es-gano-45000-pesos", Stamp(None), ASK_WHICH_PRODUCT),
    (
        "06: a typed income reaches the policy, which keeps the file's",
        "es-si-gano-10000-pesos",
        Stamp("credit_card"),
        (("run_policy", run_policy("credit_card", Decimal("10000"), None)),),
    ),
    (
        "07: asking for a person goes to a person",
        "es-quiero-hablar-con-una-persona",
        Stamp(None),
        (("hand_off_human", hand_off("customer_requested_human")),),
    ),
    (
        "07: a mortgage goes to a person",
        "es-quiero-una-hipoteca-nueva",
        Stamp(None),
        (("hand_off_scope", hand_off("out_of_scope")),),
    ),
    ("07: French goes to a person", "es-je-voudrais-une-carte-bancaire", Stamp("credit_card"), LANGUAGE_HANDOFF),
    ("07, 12: English goes to a person", "es-i-want-a-credit-card", Stamp("credit_card"), LANGUAGE_HANDOFF),
    (
        "07: English with no product goes to a person, not to the product question",
        "es-i-earn-3000-a-month",
        Stamp(None),
        LANGUAGE_HANDOFF,
    ),
    (
        "07: a reply that states an outcome is withheld and goes to a person",
        "es-si-reply-states-outcome",
        Stamp("credit_card", withheld="reply_forbidden"),
        (("hand_off_reply", hand_off("reply_forbidden")),),
    ),
    (
        "12: Spanish typed with Portuguese chosen asks for consent",
        "pt-quiero-una-tarjeta-de-credito",
        Stamp("credit_card"),
        ASK_CONSENT,
    ),
]


def test_the_fixture_files_are_the_named_fixtures() -> None:
    assert sorted(path.stem for path in TURN_FIXTURES.glob("*.json")) == sorted(FIXTURE_NAMES)
    assert sorted(path.name for path in TURN_FIXTURES.iterdir()) == sorted(f"{name}.json" for name in FIXTURE_NAMES)


def test_every_fixture_is_injected_by_a_step() -> None:
    assert {step[1] for step in STEPS} == set(FIXTURE_NAMES)


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_a_fixture_name_starts_with_its_locale(name: TurnFixtureName) -> None:
    assert name.startswith(f"{load_turn_fixture(name).locale}-")


@pytest.mark.parametrize(("name", "stamp", "expected"), [step[1:] for step in STEPS], ids=[step[0] for step in STEPS])
def test_an_injected_turn_fires_its_rule(name: TurnFixtureName, stamp: Stamp, expected: Fired) -> None:
    fixture = load_turn_fixture(name)
    assert fixture.turn.product in (None, stamp.product)
    assert (
        tuple((planned.emitted_by_rule_id, planned.command) for planned in match_rules(classified_turn(fixture, stamp)))
        == expected
    )
