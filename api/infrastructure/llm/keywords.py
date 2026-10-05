import json
import re
import unicodedata
from collections.abc import Mapping
from decimal import Decimal
from types import MappingProxyType

from api.application.cycle.ports import TurnRequest
from api.contract_models import IncomeCurrency, Intent, Locale, ProductKey, TurnLanguage
from api.domain.locale import PORTUGUESE_LOCALE, SPANISH_LOCALE
from api.domain.policy.engine import CREDIT_CARD, PERSONAL_LOAN
from api.domain.process.stored_events import (
    CHIT_CHAT_INTENT,
    CLARIFY_INTENT,
    CONFIRM_PREQUALIFY_INTENT,
    DECLINE_PREQUALIFY_INTENT,
    HUMAN_REQUEST_INTENT,
    OTHER_LANGUAGE,
    OUT_OF_SCOPE_INTENT,
    PORTUGUESE,
    PREQUALIFY_CARD_INTENT,
    PREQUALIFY_LOAN_INTENT,
    PRODUCT_INFO_INTENT,
    PROVIDE_INCOME_INTENT,
    SPANISH,
)
from api.domain.process.turns import ModelReading, ShownReading
from api.infrastructure.llm.schema import parse_conversation_turn, reading_of

# B0, the keyword baseline (M5, PLAN.md D23): the same ConversationTurn as the model, from word lists alone.
B0_MODEL = "b0-keywords"

SPANISH_WORDS = frozenset(
    [
        "quiero",
        "quisiera",
        "necesito",
        "tengo",
        "tarjeta",
        "prestamo",
        "si",
        "no",
        "gracias",
        "gano",
        "ingreso",
        "ingresos",
        "sueldo",
        "hablar",
        "persona",
        "una",
        "un",
        "el",
        "la",
        "los",
        "las",
        "productos",
        "ofrecen",
        "que",
        "cual",
        "hipoteca",
        "mejor",
        "precalificar",
        "al",
        "mensual",
        "hola",
        "buenas",
        "buenos",
    ]
)
PORTUGUESE_WORDS = frozenset(
    [
        "quero",
        "gostaria",
        "preciso",
        "tenho",
        "cartao",
        "emprestimo",
        "sim",
        "nao",
        "obrigado",
        "obrigada",
        "voce",
        "ganho",
        "renda",
        "falar",
        "pessoa",
        "uma",
        "um",
        "os",
        "produtos",
        "oferecem",
        "quais",
        "qual",
        "financiamento",
        "imobiliario",
        "investimento",
        "mensal",
        "ola",
        "oi",
        "bom",
        "atendente",
        "meu",
        "minha",
        "eu",
    ]
)
OTHER_WORDS = frozenset(
    [
        "i",
        "want",
        "would",
        "like",
        "need",
        "credit",
        "card",
        "loan",
        "earn",
        "income",
        "month",
        "the",
        "my",
        "yes",
        "please",
        "hello",
        "hi",
        "thanks",
        "je",
        "voudrais",
        "une",
        "carte",
        "bancaire",
        "oui",
        "mon",
        "merci",
        "bonjour",
    ]
)

HUMAN_WORDS = frozenset(["persona", "humano", "asesor", "pessoa", "atendente", "person", "human"])
OUT_OF_SCOPE_WORDS = frozenset(
    [
        "hipoteca",
        "hipotecario",
        "imobiliario",
        "inversion",
        "inversiones",
        "investimento",
        "mortgage",
        "debito",
        "debit",
        "limite",
        "limit",
        "disputa",
        "saldo",
    ]
)
CARD_WORDS = frozenset(["tarjeta", "cartao", "card", "carte"])
LOAN_WORDS = frozenset(["prestamo", "emprestimo", "loan"])
YES_WORDS = frozenset(["si", "sim", "yes", "claro", "dale", "ok", "vale", "acepto", "aceito", "pode", "oui"])
NO_WORDS = frozenset(["no", "nao"])
INCOME_WORDS = frozenset(
    [
        "gano",
        "ingreso",
        "ingresos",
        "sueldo",
        "salario",
        "mensual",
        "mes",
        "ganho",
        "renda",
        "mensal",
        "earn",
        "income",
        "salary",
        "month",
    ]
)
PRODUCT_INFO_WORDS = frozenset(
    ["productos", "produtos", "products", "ofrecen", "oferecem", "offer", "tasa", "taxa", "rate", "requisitos"]
)
CREDIT_WORDS = frozenset(["credito", "credit"])
GREETING_WORDS = frozenset(
    ["hola", "ola", "oi", "hello", "hi", "buenas", "buenos", "bom", "gracias", "obrigado", "obrigada", "thanks"]
)

MXN: IncomeCurrency = "MXN"
COP: IncomeCurrency = "COP"
ARS: IncomeCurrency = "ARS"
CURRENCY_WORDS: Mapping[str, IncomeCurrency] = MappingProxyType({"mxn": MXN, "cop": COP, "ars": ARS})
CURRENCY_PHRASES: Mapping[str, IncomeCurrency] = MappingProxyType(
    {"pesos mexicanos": MXN, "pesos colombianos": COP, "pesos argentinos": ARS}
)

THOUSANDS = re.compile(r"\d{1,3}(?:([.,])\d{3})(?:\1\d{3})*")
DECIMAL = re.compile(r"\d+(?:[.,]\d{1,2})?")
NUMBER = re.compile(r"\d[\d.,]*")
WORD = re.compile(r"[a-z]+")

# The reply text is a fixed sentence per intent, in the language chosen with the switch (D21). It is shown only
# for clarify, product_info, chit_chat, and decline_prequalify; the rules send a template or a handoff otherwise.
REPLIES: Mapping[Locale, Mapping[Intent, str]] = MappingProxyType(
    {
        SPANISH_LOCALE: MappingProxyType(
            {
                CLARIFY_INTENT: "¿Te interesa una tarjeta de crédito o un préstamo personal?",
                PRODUCT_INFO_INTENT: (
                    "Te puedo ayudar con una tarjeta de crédito o un préstamo personal. ¿Cuál te interesa?"
                ),
                CHIT_CHAT_INTENT: "Hola, soy Alba. Te puedo ayudar con una tarjeta de crédito o un préstamo personal.",
                DECLINE_PREQUALIFY_INTENT: "Entendido. Si cambias de opinión, aquí estoy.",
            }
        ),
        PORTUGUESE_LOCALE: MappingProxyType(
            {
                CLARIFY_INTENT: "Você tem interesse em um cartão de crédito ou em um empréstimo pessoal?",
                PRODUCT_INFO_INTENT: (
                    "Posso ajudar com um cartão de crédito ou um empréstimo pessoal. Qual deles te interessa?"
                ),
                CHIT_CHAT_INTENT: "Olá, sou a Alba. Posso ajudar com um cartão de crédito ou um empréstimo pessoal.",
                DECLINE_PREQUALIFY_INTENT: "Entendido. Se mudar de ideia, é só me escrever.",
            }
        ),
    }
)
ACKNOWLEDGEMENT: Mapping[Locale, str] = MappingProxyType(
    {SPANISH_LOCALE: "Con gusto te ayudo.", PORTUGUESE_LOCALE: "Com prazer, posso ajudar."}
)


# The turn goes through the model's own JSON parse, so B0 cannot hand the cycle a turn the model could not.
def read_keyword_turn(request: TurnRequest) -> ModelReading:
    raw_response = json.dumps(keyword_turn(request.text, request.locale), ensure_ascii=False)
    return ShownReading(reading_of(parse_conversation_turn(raw_response)))


def keyword_turn(text: str, locale: Locale) -> dict[str, object]:
    folded = fold(text)
    words = WORD.findall(folded)
    amount = income_amount(folded, words)
    intent, product = classify_intent(set(words), words, amount)
    reply = REPLIES[locale].get(intent, ACKNOWLEDGEMENT[locale])
    return {
        "intent": intent,
        "product": product,
        "declared_income_amount": json_number(amount),
        "declared_income_currency": currency(folded, words) if amount is not None else None,
        "language": language(words, locale),
        "needs_clarification": intent == CLARIFY_INTENT,
        "clarification_question": reply if intent == CLARIFY_INTENT else None,
        "reply_text": reply,
    }


# json writes an int exactly and a float by its shortest round trip, which the exact parse reads back unchanged.
def json_number(amount: Decimal | None) -> int | float | None:
    if amount is None:
        return None
    return int(amount) if amount == amount.to_integral_value() else float(amount)


def fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def classify_intent(vocabulary: set[str], words: list[str], amount: Decimal | None) -> tuple[Intent, ProductKey | None]:
    if vocabulary & HUMAN_WORDS:
        return HUMAN_REQUEST_INTENT, None
    if vocabulary & OUT_OF_SCOPE_WORDS:
        return OUT_OF_SCOPE_INTENT, None
    card, loan = bool(vocabulary & CARD_WORDS), bool(vocabulary & LOAN_WORDS)
    if card != loan:
        return (PREQUALIFY_CARD_INTENT, CREDIT_CARD) if card else (PREQUALIFY_LOAN_INTENT, PERSONAL_LOAN)
    if vocabulary & YES_WORDS:
        return CONFIRM_PREQUALIFY_INTENT, None
    if amount is not None:
        return PROVIDE_INCOME_INTENT, None
    if words and words[0] in NO_WORDS:
        return DECLINE_PREQUALIFY_INTENT, None
    if vocabulary & PRODUCT_INFO_WORDS:
        return PRODUCT_INFO_INTENT, None
    if vocabulary & GREETING_WORDS and not vocabulary & CREDIT_WORDS:
        return CHIT_CHAT_INTENT, None
    return CLARIFY_INTENT, None


def income_amount(folded: str, words: list[str]) -> Decimal | None:
    if not set(words) & INCOME_WORDS:
        return None
    for match in NUMBER.finditer(folded):
        number = match.group().rstrip(".,")
        if THOUSANDS.fullmatch(number):
            return Decimal(number.replace(",", "").replace(".", ""))
        if DECIMAL.fullmatch(number):
            return Decimal(number.replace(",", "."))
    return None


def currency(folded: str, words: list[str]) -> IncomeCurrency | None:
    for phrase, code in CURRENCY_PHRASES.items():
        if phrase in folded:
            return code
    for word in words:
        if word in CURRENCY_WORDS:
            return CURRENCY_WORDS[word]
    return None


def language(words: list[str], locale: Locale) -> TurnLanguage:
    spanish = sum(word in SPANISH_WORDS for word in words)
    portuguese = sum(word in PORTUGUESE_WORDS for word in words)
    other = sum(word in OTHER_WORDS for word in words)
    if other > max(spanish, portuguese):
        return OTHER_LANGUAGE
    if spanish != portuguese:
        return SPANISH if spanish > portuguese else PORTUGUESE
    return SPANISH if locale == SPANISH_LOCALE else PORTUGUESE
