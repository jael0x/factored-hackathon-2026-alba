from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from api.contract_models import Locale, ProductKey, ReasonCode
from api.domain.process.events import TURN_CLASSIFIED
from api.domain.process.lifecycle import AI_ACTIVE
from api.domain.process.stored_events import StoredEvent, parse_stored_event
from api.infrastructure.llm.schema import ConversationTurn, decode_exact_json

TURN_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "turns"
EVENT_ID = UUID("44444444-4444-4444-8444-444444444444")
PROCESS_ID = UUID("22222222-2222-4222-8222-222222222222")

TurnFixtureName = Literal[
    "es-quiero-un-credito",
    "es-el-credito",
    "es-una-tarjeta-de-credito",
    "es-quiero-una-tarjeta-de-credito",
    "es-mejor-si-quiero-la-tarjeta",
    "es-quiero-un-prestamo-personal",
    "es-si",
    "es-si-quiero-precalificar",
    "es-si-gano-45000-pesos",
    "es-si-gano-10000-pesos",
    "es-gano-45000-pesos",
    "es-no-gracias",
    "es-que-productos-ofrecen",
    "es-quiero-hablar-con-una-persona",
    "es-quiero-una-hipoteca-nueva",
    "es-je-voudrais-une-carte-bancaire",
    "es-i-want-a-credit-card",
    "es-i-earn-3000-a-month",
    "es-si-reply-states-outcome",
    "pt-sim",
    "pt-cartao-de-credito",
    "pt-quiero-una-tarjeta-de-credito",
]


class TurnFixture(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    text: str
    locale: Locale
    turn: ConversationTurn


@dataclass(frozen=True)
class Stamp:
    product: ProductKey | None
    product_asked_count: int = 0
    income_requested: bool = False
    withheld: ReasonCode | None = None


def load_turn_fixture(name: TurnFixtureName) -> TurnFixture:
    return TurnFixture.model_validate(decode_exact_json((TURN_FIXTURES / f"{name}.json").read_bytes()))


def classified_turn(fixture: TurnFixture, stamp: Stamp) -> StoredEvent:
    turn = fixture.turn
    payload: dict[str, object] = {
        "intent": turn.intent,
        "product": stamp.product,
        "language": turn.language,
        "locale": fixture.locale,
        "declared_income_amount": turn.declared_income_amount,
        "declared_income_currency": turn.declared_income_currency,
        "reply_text": turn.reply_text,
        "reply_ok": stamp.withheld is None,
        "reason_code": stamp.withheld,
        "product_asked_count": stamp.product_asked_count,
        "income_requested": stamp.income_requested,
    }
    return parse_stored_event(EVENT_ID, TURN_CLASSIFIED, PROCESS_ID, AI_ACTIVE, payload)
