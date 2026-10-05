from collections.abc import Mapping
from types import MappingProxyType

from api.contract_models import CloseOutcome, DecidedBy, Locale, Outcome, ProductKey, TemplateId
from api.domain.closed_sets import parse_member
from api.domain.locale import LOCALES, PORTUGUESE_LOCALE, SPANISH_LOCALE
from api.domain.policy.engine import CREDIT_CARD, NOT_PREQUALIFIED, PERSONAL_LOAN, PREQUALIFIED
from api.domain.process.commands import (
    CONFIRM_PREQUALIFY_TEMPLATE,
    DECIDED_BY_CONSULTANT,
    DECIDED_BY_POLICY,
    NEEDS_INCOME,
    PRODUCT_CASE_OPEN,
    REFER_NOTICE,
    WHICH_PRODUCT,
)
from api.domain.process.stored_events import CLOSE_OUTCOMES, DECIDED_BY, PRODUCT_KEYS, TEMPLATE_IDS

PRODUCT_SLOT = "{product}"


Texts = Mapping[Locale, str]

PRODUCT_NAMES: Mapping[Locale, Mapping[ProductKey, str]] = MappingProxyType(
    {
        SPANISH_LOCALE: MappingProxyType(
            {CREDIT_CARD: "una tarjeta de crédito", PERSONAL_LOAN: "un préstamo personal"}
        ),
        PORTUGUESE_LOCALE: MappingProxyType(
            {CREDIT_CARD: "um cartão de crédito", PERSONAL_LOAN: "um empréstimo pessoal"}
        ),
    }
)

NOTICES_FOR_A_PRODUCT: Mapping[TemplateId, Texts] = MappingProxyType(
    {
        CONFIRM_PREQUALIFY_TEMPLATE: MappingProxyType(
            {
                SPANISH_LOCALE: "¿Quieres que revise si precalificas para {product}? Es una precalificación simulada: "
                "usa los datos que el banco ya tiene y no abre ningún producto. Responde sí o no.",
                PORTUGUESE_LOCALE: "Quer que eu verifique se você pré-qualifica para {product}? É uma pré-qualificação "
                "simulada: usa os dados que o banco já tem e não abre nenhum produto. Responda sim ou não.",
            }
        ),
        NEEDS_INCOME: MappingProxyType(
            {
                SPANISH_LOCALE: "Para seguir con la precalificación para {product}, necesito tu ingreso mensual en "
                "pesos. ¿Cuánto ganas al mes?",
                PORTUGUESE_LOCALE: "Para continuar a pré-qualificação para {product}, preciso da sua renda mensal em "
                "pesos. Quanto você ganha por mês?",
            }
        ),
        REFER_NOTICE: MappingProxyType(
            {
                SPANISH_LOCALE: "Una persona del banco va a revisar tu solicitud de {product}. Te avisaremos por aquí "
                "cuando tenga una respuesta.",
                PORTUGUESE_LOCALE: "Uma pessoa do banco vai analisar sua solicitação de {product}. Avisaremos por aqui "
                "quando houver uma resposta.",
            }
        ),
        PRODUCT_CASE_OPEN: MappingProxyType(
            {
                SPANISH_LOCALE: "Ya tienes una conversación abierta sobre {product}. Ábrela desde el inicio para seguir "
                "con ella.",
                PORTUGUESE_LOCALE: "Você já tem uma conversa aberta sobre {product}. Abra-a pelo início para continuar.",
            }
        ),
    }
)

NOTICES_FOR_ANY_PRODUCT: Mapping[TemplateId, Texts] = MappingProxyType(
    {
        WHICH_PRODUCT: MappingProxyType(
            {
                SPANISH_LOCALE: "¿Sobre cuál producto quieres consultar: "
                f"{PRODUCT_NAMES[SPANISH_LOCALE][CREDIT_CARD]} o {PRODUCT_NAMES[SPANISH_LOCALE][PERSONAL_LOAN]}?",
                PORTUGUESE_LOCALE: "Sobre qual produto você quer consultar: "
                f"{PRODUCT_NAMES[PORTUGUESE_LOCALE][CREDIT_CARD]} ou "
                f"{PRODUCT_NAMES[PORTUGUESE_LOCALE][PERSONAL_LOAN]}?",
            }
        ),
    }
)

CERTIFICATES: Mapping[tuple[DecidedBy, Outcome], Texts] = MappingProxyType(
    {
        (DECIDED_BY_POLICY, PREQUALIFIED): MappingProxyType(
            {
                SPANISH_LOCALE: "Precalificas para {product}. Es una precalificación simulada: no abre el producto ni "
                "mueve dinero.",
                PORTUGUESE_LOCALE: "Você pré-qualifica para {product}. É uma pré-qualificação simulada: não abre o "
                "produto nem movimenta dinheiro.",
            }
        ),
        (DECIDED_BY_POLICY, NOT_PREQUALIFIED): MappingProxyType(
            {
                SPANISH_LOCALE: "No precalificas para {product} por ahora. Es una precalificación simulada con los "
                "datos de tu expediente.",
                PORTUGUESE_LOCALE: "Você não pré-qualifica para {product} no momento. É uma pré-qualificação simulada "
                "com os dados do seu cadastro.",
            }
        ),
        (DECIDED_BY_CONSULTANT, PREQUALIFIED): MappingProxyType(
            {
                SPANISH_LOCALE: "Una persona del banco revisó tu solicitud: precalificas para {product}. Es una "
                "precalificación simulada: no abre el producto ni mueve dinero.",
                PORTUGUESE_LOCALE: "Uma pessoa do banco analisou sua solicitação: você pré-qualifica para {product}. "
                "É uma pré-qualificação simulada: não abre o produto nem movimenta dinheiro.",
            }
        ),
        (DECIDED_BY_CONSULTANT, NOT_PREQUALIFIED): MappingProxyType(
            {
                SPANISH_LOCALE: "Una persona del banco revisó tu solicitud: no precalificas para {product} por ahora.",
                PORTUGUESE_LOCALE: "Uma pessoa do banco analisou sua solicitação: você não pré-qualifica para "
                "{product} no momento.",
            }
        ),
    }
)


class MissingProduct(Exception):
    def __init__(self, template: str) -> None:
        super().__init__(f"{template} names the product, and none was given")


def render_notice(template_id: TemplateId, locale: Locale, product: ProductKey | None) -> str:
    if template_id in NOTICES_FOR_ANY_PRODUCT:
        return NOTICES_FOR_ANY_PRODUCT[template_id][locale]
    if product is None:
        raise MissingProduct(template_id)
    return name_product(NOTICES_FOR_A_PRODUCT[template_id][locale], locale, product)


def certificate_for_policy(outcome: Outcome, locale: Locale, product: ProductKey) -> str:
    closing = parse_member(outcome, CLOSE_OUTCOMES, "certificate outcome")
    return render_certificate(DECIDED_BY_POLICY, closing, locale, product)


def certificate_for_close(outcome: CloseOutcome, locale: Locale, product: ProductKey | None) -> str:
    if product is None:
        raise MissingProduct("the consultant certificate")
    return render_certificate(DECIDED_BY_CONSULTANT, outcome, locale, product)


def render_certificate(decided_by: DecidedBy, outcome: CloseOutcome, locale: Locale, product: ProductKey) -> str:
    return name_product(CERTIFICATES[(decided_by, outcome)][locale], locale, product)


def name_product(text: str, locale: Locale, product: ProductKey) -> str:
    return text.replace(PRODUCT_SLOT, PRODUCT_NAMES[locale][product])


def require_every_locale[Key](texts: Mapping[Key, Texts], label: str) -> None:
    incomplete = sorted(str(key) for key, by_locale in texts.items() if set(by_locale) != LOCALES)
    if incomplete:
        raise ValueError(f"{label} must have a text for every locale: {incomplete}")


def require_slot[Key](texts: Mapping[Key, Texts], expected: int, label: str) -> None:
    wrong = sorted(
        f"{key} {locale}"
        for key, by_locale in texts.items()
        for locale, text in by_locale.items()
        if text.count(PRODUCT_SLOT) != expected
    )
    if wrong:
        raise ValueError(f"{label} must name the product {expected} time(s): {wrong}")


def require_notices(for_a_product: Mapping[TemplateId, Texts], for_any_product: Mapping[TemplateId, Texts]) -> None:
    listed = [*for_a_product, *for_any_product]
    if len(listed) != len(set(listed)) or set(listed) != TEMPLATE_IDS:
        raise ValueError(f"every template id needs exactly one notice: {sorted(TEMPLATE_IDS)}")
    require_every_locale(for_a_product, "a notice")
    require_every_locale(for_any_product, "a notice")
    require_slot(for_a_product, 1, "a notice for a product")
    require_slot(for_any_product, 0, "a notice for any product")


def require_certificates(certificates: Mapping[tuple[DecidedBy, Outcome], Texts]) -> None:
    expected = {(decided_by, outcome) for decided_by in DECIDED_BY for outcome in CLOSE_OUTCOMES}
    if set(certificates) != expected:
        raise ValueError("every decider and close outcome needs exactly one certificate")
    require_every_locale(certificates, "a certificate")
    require_slot(certificates, 1, "a certificate")


def require_product_names(names: Mapping[Locale, Mapping[ProductKey, str]]) -> None:
    if set(names) != LOCALES or any(set(by_product) != PRODUCT_KEYS for by_product in names.values()):
        raise ValueError("every locale needs a name for every product")


require_product_names(PRODUCT_NAMES)
require_notices(NOTICES_FOR_A_PRODUCT, NOTICES_FOR_ANY_PRODUCT)
require_certificates(CERTIFICATES)
