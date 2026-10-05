from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from api.contract_models import IncomeCurrency, Intent, ProductKey, ReasonCode, TurnLanguage
from api.domain.policy.engine import NEEDS_INFO
from api.domain.process.commands import CONFIRM_PREQUALIFY_TEMPLATE, WHICH_PRODUCT
from api.domain.process.stored_events import (
    CLARIFY_INTENT,
    DECLINE_PREQUALIFY_INTENT,
    TEMPLATE_LANGUAGES,
    AnalysisCompleted,
    ShownTurn,
    StoredEvent,
    TemplateSent,
)


@dataclass(frozen=True)
class TurnReading:
    intent: Intent
    product: ProductKey | None
    language: TurnLanguage
    declared_income_amount: Decimal | None
    declared_income_currency: IncomeCurrency | None
    reply_text: str


@dataclass(frozen=True)
class ShownReading:
    reading: TurnReading


@dataclass(frozen=True)
class WithheldReading:
    reading: TurnReading
    reason_code: ReasonCode


ModelReading = ShownReading | WithheldReading


@dataclass(frozen=True)
class TurnStamp:
    product: ProductKey | None
    product_asked_count: int
    income_requested: bool


def stamp_turn(earlier: Sequence[StoredEvent], read_product: ProductKey | None, stored: ProductKey | None) -> TurnStamp:
    product = stored if read_product is None else read_product
    return TurnStamp(
        product=product,
        product_asked_count=count_product_asks(earlier),
        income_requested=income_was_requested(earlier, product),
    )


def count_product_asks(earlier: Sequence[StoredEvent]) -> int:
    return sum(1 for event in earlier if asked_which_product(event))


def asked_which_product(event: StoredEvent) -> bool:
    if isinstance(event, TemplateSent):
        return event.template_id == WHICH_PRODUCT
    return (
        isinstance(event, ShownTurn)
        and event.intent == CLARIFY_INTENT
        and event.product is None
        and event.language in TEMPLATE_LANGUAGES
    )


def income_was_requested(earlier: Sequence[StoredEvent], product: ProductKey | None) -> bool:
    for index in range(len(earlier) - 1, -1, -1):
        latest = earlier[index]
        if isinstance(latest, AnalysisCompleted):
            asked = latest.outcome == NEEDS_INFO and latest.product == product
            return asked and not any(withdraws_the_request(event) for event in earlier[index + 1 :])
    return False


def withdraws_the_request(event: StoredEvent) -> bool:
    if isinstance(event, TemplateSent):
        return event.template_id == CONFIRM_PREQUALIFY_TEMPLATE
    return isinstance(event, ShownTurn) and event.intent == DECLINE_PREQUALIFY_INTENT
