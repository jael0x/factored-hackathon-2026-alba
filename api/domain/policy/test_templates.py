from collections.abc import Mapping
from datetime import date
from decimal import Decimal
from types import MappingProxyType

import pytest

from api.contract_models import CloseOutcome, DecidedBy, Locale, Outcome, ProductKey, TemplateId
from api.domain.policy.engine import CreditProfile, Decision, decide
from api.domain.policy.templates import (
    CERTIFICATES,
    NOTICES_FOR_A_PRODUCT,
    NOTICES_FOR_ANY_PRODUCT,
    PRODUCT_NAMES,
    MissingProduct,
    Texts,
    certificate_for_close,
    certificate_for_policy,
    render_notice,
    require_certificates,
    require_notices,
    require_product_names,
)

AS_OF = date(2026, 6, 17)
TEMPLATES: tuple[TemplateId, ...] = ("confirm_prequalify", "which_product", "needs_income", "refer_notice")
BOTH_LOCALES: tuple[Locale, ...] = ("es", "pt")
CLOSES: tuple[CloseOutcome, ...] = ("PREQUALIFIED", "NOT_PREQUALIFIED")


def decision_for(*, credit_score: int | None, income_local: Decimal | None, max_days_past_due: int = 0) -> Decision:
    profile = CreditProfile(
        customer_status="Active",
        credit_score=credit_score,
        income_local=income_local,
        income_currency="MXN",
        income_usd=None,
        max_days_past_due=max_days_past_due,
        has_active_card=False,
        has_active_personal_loan=False,
        as_of=AS_OF,
    )
    return decide(profile, "credit_card", None)


JUAN = decision_for(credit_score=812, income_local=Decimal("306753.45"))
MARIANA = decision_for(credit_score=515, income_local=Decimal("801583.70"), max_days_past_due=180)
ALICIA = decision_for(credit_score=615, income_local=Decimal("4707334.28"))
JULIANA = decision_for(credit_score=714, income_local=None)


def test_every_notice_reads_as_written_for_a_card() -> None:
    rendered = {
        (template_id, locale): render_notice(template_id, locale, "credit_card")
        for template_id in TEMPLATES
        for locale in BOTH_LOCALES
    }
    assert rendered == {
        ("confirm_prequalify", "es"): "¿Quieres que revise si precalificas para una tarjeta de crédito? Es una "
        "precalificación simulada: usa los datos que el banco ya tiene y no abre ningún producto. Responde sí o no.",
        ("confirm_prequalify", "pt"): "Quer que eu verifique se você pré-qualifica para um cartão de crédito? É uma "
        "pré-qualificação simulada: usa os dados que o banco já tem e não abre nenhum produto. Responda sim ou não.",
        ("which_product", "es"): "¿Sobre cuál producto quieres consultar: una tarjeta de crédito o un préstamo "
        "personal?",
        ("which_product", "pt"): "Sobre qual produto você quer consultar: um cartão de crédito ou um empréstimo "
        "pessoal?",
        ("needs_income", "es"): "Para seguir con la precalificación para una tarjeta de crédito, necesito tu ingreso "
        "mensual en pesos. ¿Cuánto ganas al mes?",
        ("needs_income", "pt"): "Para continuar a pré-qualificação para um cartão de crédito, preciso da sua renda "
        "mensal em pesos. Quanto você ganha por mês?",
        ("refer_notice", "es"): "Una persona del banco va a revisar tu solicitud de una tarjeta de crédito. Te "
        "avisaremos por aquí cuando tenga una respuesta.",
        ("refer_notice", "pt"): "Uma pessoa do banco vai analisar sua solicitação de um cartão de crédito. Avisaremos "
        "por aqui quando houver uma resposta.",
    }


@pytest.mark.parametrize(
    ("locale", "expected"),
    [
        ("es", "¿Quieres que revise si precalificas para un préstamo personal?"),
        ("pt", "Quer que eu verifique se você pré-qualifica para um empréstimo pessoal?"),
    ],
)
def test_a_notice_names_the_product_it_was_given(locale: Locale, expected: str) -> None:
    assert render_notice("confirm_prequalify", locale, "personal_loan").startswith(expected)


@pytest.mark.parametrize("product", ["credit_card", "personal_loan", None])
def test_the_product_question_is_the_same_whatever_product_is_known(product: ProductKey | None) -> None:
    assert render_notice("which_product", "es", product) == (
        "¿Sobre cuál producto quieres consultar: una tarjeta de crédito o un préstamo personal?"
    )


@pytest.mark.parametrize("template_id", ["confirm_prequalify", "needs_income", "refer_notice"])
def test_a_notice_that_names_the_product_refuses_to_render_without_one(template_id: TemplateId) -> None:
    with pytest.raises(MissingProduct, match=f"{template_id} names the product, and none was given"):
        render_notice(template_id, "es", None)


@pytest.mark.parametrize("locale", ["es", "pt"])
def test_the_referral_notice_states_no_outcome_and_no_score(locale: Locale) -> None:
    notice = render_notice("refer_notice", locale, "credit_card").lower()
    assert [word for word in ("precalific", "pré-qualific", "score", "puntaje", "pontuação") if word in notice] == []


def test_the_policy_certificate_reads_as_written_for_each_close_outcome() -> None:
    rendered = {
        (decision.outcome, locale): certificate_for_policy(decision.outcome, locale, "credit_card")
        for decision in (JUAN, MARIANA)
        for locale in BOTH_LOCALES
    }
    assert rendered == {
        ("PREQUALIFIED", "es"): "Precalificas para una tarjeta de crédito. Es una precalificación simulada: no abre "
        "el producto ni mueve dinero.",
        ("PREQUALIFIED", "pt"): "Você pré-qualifica para um cartão de crédito. É uma pré-qualificação simulada: não "
        "abre o produto nem movimenta dinheiro.",
        ("NOT_PREQUALIFIED", "es"): "No precalificas para una tarjeta de crédito por ahora. Es una precalificación "
        "simulada con los datos de tu expediente.",
        ("NOT_PREQUALIFIED", "pt"): "Você não pré-qualifica para um cartão de crédito no momento. É uma "
        "pré-qualificação simulada com os dados do seu cadastro.",
    }


@pytest.mark.parametrize("decision", [ALICIA, JULIANA], ids=["refer", "needs_info"])
def test_a_decision_that_does_not_close_the_case_has_no_certificate(decision: Decision) -> None:
    with pytest.raises(ValueError, match=f"certificate outcome '{decision.outcome}' is not one of"):
        certificate_for_policy(decision.outcome, "es", "credit_card")


def test_the_consultant_certificate_says_a_person_reviewed_the_request() -> None:
    rendered = {
        (outcome, locale): certificate_for_close(outcome, locale, "personal_loan")
        for outcome in CLOSES
        for locale in BOTH_LOCALES
    }
    assert rendered == {
        ("PREQUALIFIED", "es"): "Una persona del banco revisó tu solicitud: precalificas para un préstamo personal. "
        "Es una precalificación simulada: no abre el producto ni mueve dinero.",
        ("PREQUALIFIED", "pt"): "Uma pessoa do banco analisou sua solicitação: você pré-qualifica para um "
        "empréstimo pessoal. É uma pré-qualificação simulada: não abre o produto nem movimenta dinheiro.",
        ("NOT_PREQUALIFIED", "es"): "Una persona del banco revisó tu solicitud: no precalificas para un préstamo "
        "personal por ahora.",
        ("NOT_PREQUALIFIED", "pt"): "Uma pessoa do banco analisou sua solicitação: você não pré-qualifica para um "
        "empréstimo pessoal no momento.",
    }


def test_a_consultant_certificate_without_a_product_is_refused() -> None:
    with pytest.raises(MissingProduct, match="the consultant certificate names the product"):
        certificate_for_close("PREQUALIFIED", "es", None)


def test_the_tables_the_module_loads_pass_their_own_checks() -> None:
    require_product_names(PRODUCT_NAMES)
    require_notices(NOTICES_FOR_A_PRODUCT, NOTICES_FOR_ANY_PRODUCT)
    require_certificates(CERTIFICATES)


def test_a_notice_missing_a_locale_is_refused() -> None:
    spanish: Texts = MappingProxyType({"es": "¿Cuál?"})
    spanish_only: dict[TemplateId, Texts] = {**NOTICES_FOR_ANY_PRODUCT, "which_product": spanish}
    with pytest.raises(ValueError, match=r"a notice must have a text for every locale: \['which_product'\]"):
        require_notices(NOTICES_FOR_A_PRODUCT, spanish_only)


def test_a_template_id_without_a_notice_is_refused() -> None:
    without_income: dict[TemplateId, Texts] = {
        key: texts for key, texts in NOTICES_FOR_A_PRODUCT.items() if key != "needs_income"
    }
    with pytest.raises(ValueError, match="every template id needs exactly one notice"):
        require_notices(without_income, NOTICES_FOR_ANY_PRODUCT)


def test_a_template_id_listed_in_both_tables_is_refused() -> None:
    twice: dict[TemplateId, Texts] = {**NOTICES_FOR_ANY_PRODUCT, "needs_income": NOTICES_FOR_A_PRODUCT["needs_income"]}
    with pytest.raises(ValueError, match="every template id needs exactly one notice"):
        require_notices(NOTICES_FOR_A_PRODUCT, twice)


def test_a_notice_for_a_product_that_does_not_name_it_is_refused() -> None:
    plain: Texts = MappingProxyType({"es": "Revisaremos.", "pt": "Vamos ver."})
    unnamed: dict[TemplateId, Texts] = {**NOTICES_FOR_A_PRODUCT, "refer_notice": plain}
    with pytest.raises(ValueError, match=r"name the product 1 time\(s\): \['refer_notice es', 'refer_notice pt'\]"):
        require_notices(unnamed, NOTICES_FOR_ANY_PRODUCT)


def test_a_notice_for_any_product_that_names_one_is_refused() -> None:
    slotted: Texts = MappingProxyType({"es": "¿{product}?", "pt": "Qual?"})
    named: dict[TemplateId, Texts] = {"which_product": slotted}
    with pytest.raises(ValueError, match=r"name the product 0 time\(s\): \['which_product es'\]"):
        require_notices(NOTICES_FOR_A_PRODUCT, named)


def test_a_missing_certificate_is_refused() -> None:
    policy_only: dict[tuple[DecidedBy, Outcome], Texts] = {
        key: texts for key, texts in CERTIFICATES.items() if key[0] == "policy"
    }
    with pytest.raises(ValueError, match="every decider and close outcome needs exactly one certificate"):
        require_certificates(policy_only)


def test_a_certificate_for_an_outcome_that_does_not_close_is_refused() -> None:
    with_refer: dict[tuple[DecidedBy, Outcome], Texts] = {
        **CERTIFICATES,
        ("policy", "REFER"): CERTIFICATES[("policy", "PREQUALIFIED")],
    }
    with pytest.raises(ValueError, match="every decider and close outcome needs exactly one certificate"):
        require_certificates(with_refer)


def test_a_certificate_missing_a_locale_is_refused() -> None:
    spanish: Texts = MappingProxyType({"es": "Sí {product}."})
    spanish_only: dict[tuple[DecidedBy, Outcome], Texts] = {**CERTIFICATES, ("consultant", "PREQUALIFIED"): spanish}
    with pytest.raises(ValueError, match="a certificate must have a text for every locale"):
        require_certificates(spanish_only)


def test_a_certificate_that_does_not_name_the_product_is_refused() -> None:
    plain: Texts = MappingProxyType({"es": "Sí.", "pt": "Sim."})
    unnamed: dict[tuple[DecidedBy, Outcome], Texts] = {**CERTIFICATES, ("policy", "PREQUALIFIED"): plain}
    with pytest.raises(ValueError, match="a certificate must name the product 1 time"):
        require_certificates(unnamed)


def test_a_locale_without_every_product_name_is_refused() -> None:
    card: Mapping[ProductKey, str] = MappingProxyType({"credit_card": "um cartão de crédito"})
    cards_only: dict[Locale, Mapping[ProductKey, str]] = {**PRODUCT_NAMES, "pt": card}
    with pytest.raises(ValueError, match="every locale needs a name for every product"):
        require_product_names(cards_only)


def test_a_missing_locale_for_product_names_is_refused() -> None:
    with pytest.raises(ValueError, match="every locale needs a name for every product"):
        require_product_names({"es": PRODUCT_NAMES["es"]})
