from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import get_args
from uuid import UUID

from api.contract_models import (
    CloseOutcome,
    DecidedBy,
    EventName,
    IncomeCurrency,
    Intent,
    Locale,
    Outcome,
    ProcessState,
    ProductKey,
    ReasonCode,
    TurnLanguage,
)
from api.domain.closed_sets import parse_member
from api.domain.locale import LOCALES
from api.domain.process.events import (
    ANALYSIS_COMPLETED,
    CONSULTANT_CLOSED,
    MESSAGE_RECEIVED,
    PREQUALIFICATION_DECIDED,
    TURN_CLASSIFIED,
)
from api.domain.process.lifecycle import (
    AI_ACTIVE,
    ENDED,
    MODEL_OUTPUT_INVALID,
    REASON_CODES,
    REPLY_FORBIDDEN,
    parse_state,
)

PRODUCT_INFO_INTENT: Intent = "product_info"
PREQUALIFY_CARD_INTENT: Intent = "prequalify_card"
PREQUALIFY_LOAN_INTENT: Intent = "prequalify_loan"
CONFIRM_PREQUALIFY_INTENT: Intent = "confirm_prequalify"
DECLINE_PREQUALIFY_INTENT: Intent = "decline_prequalify"
PROVIDE_INCOME_INTENT: Intent = "provide_income"
HUMAN_REQUEST_INTENT: Intent = "human_request"
OUT_OF_SCOPE_INTENT: Intent = "out_of_scope"
CLARIFY_INTENT: Intent = "clarify"
CHIT_CHAT_INTENT: Intent = "chit_chat"

SPANISH: TurnLanguage = "es"
PORTUGUESE: TurnLanguage = "pt"
OTHER_LANGUAGE: TurnLanguage = "other"
TEMPLATE_LANGUAGES: frozenset[TurnLanguage] = frozenset({SPANISH, PORTUGUESE})

WITHHELD_REASONS: frozenset[ReasonCode] = frozenset({REPLY_FORBIDDEN, MODEL_OUTPUT_INVALID})

EVENT_NAMES: frozenset[EventName] = frozenset(get_args(EventName))
INTENTS: frozenset[Intent] = frozenset(get_args(Intent))
TURN_LANGUAGES: frozenset[TurnLanguage] = frozenset(get_args(TurnLanguage))
PRODUCT_KEYS: frozenset[ProductKey] = frozenset(get_args(ProductKey))
INCOME_CURRENCIES: frozenset[IncomeCurrency] = frozenset(get_args(IncomeCurrency))
OUTCOMES: frozenset[Outcome] = frozenset(get_args(Outcome))
CLOSE_OUTCOMES: frozenset[CloseOutcome] = frozenset(get_args(CloseOutcome))
DECIDED_BY: frozenset[DecidedBy] = frozenset(get_args(DecidedBy))

Payload = Mapping[str, object]


@dataclass(frozen=True)
class MessageReceived:
    event_id: UUID
    process_id: UUID | None
    process_state: ProcessState
    locale: Locale


@dataclass(frozen=True)
class ShownTurn:
    event_id: UUID
    intent: Intent
    product: ProductKey | None
    language: TurnLanguage
    declared_income_amount: Decimal | None
    declared_income_currency: IncomeCurrency | None
    product_asked_count: int
    income_requested: bool


@dataclass(frozen=True)
class WithheldTurn:
    event_id: UUID
    reason_code: ReasonCode


@dataclass(frozen=True)
class AnalysisCompleted:
    event_id: UUID
    outcome: Outcome


@dataclass(frozen=True)
class PrequalificationDecided:
    event_id: UUID
    outcome: CloseOutcome
    decided_by: DecidedBy


@dataclass(frozen=True)
class ConsultantClosed:
    event_id: UUID
    outcome: CloseOutcome


@dataclass(frozen=True)
class NoRuleEvent:
    event_id: UUID
    event_name: EventName


TurnClassified = ShownTurn | WithheldTurn
StoredEvent = (
    MessageReceived | TurnClassified | AnalysisCompleted | PrequalificationDecided | ConsultantClosed | NoRuleEvent
)


def parse_stored_event(
    event_id: UUID,
    event_name: object,
    process_id: UUID | None,
    process_state: object,
    payload: Payload,
) -> StoredEvent:
    name = parse_member(event_name, EVENT_NAMES, "event name")
    if name == MESSAGE_RECEIVED:
        return parse_message(event_id, process_id, process_state, payload)
    if name == TURN_CLASSIFIED:
        return parse_turn(event_id, payload)
    if name == ANALYSIS_COMPLETED:
        return AnalysisCompleted(event_id, parse_member(field(payload, "outcome"), OUTCOMES, "outcome"))
    if name == PREQUALIFICATION_DECIDED:
        return PrequalificationDecided(
            event_id,
            outcome=parse_close_outcome(payload),
            decided_by=parse_member(field(payload, "decided_by"), DECIDED_BY, "decided_by"),
        )
    if name == CONSULTANT_CLOSED:
        return ConsultantClosed(event_id, outcome=parse_close_outcome(payload))
    return NoRuleEvent(event_id, name)


def parse_message(event_id: UUID, process_id: UUID | None, process_state: object, payload: Payload) -> MessageReceived:
    state = parse_state(process_state)
    if state == ENDED:
        raise ValueError("a message is never stamped with an ended process")
    if process_id is None and state != AI_ACTIVE:
        raise ValueError(f"a message with no process is stamped {AI_ACTIVE}, not {state}")
    return MessageReceived(event_id, process_id, state, parse_member(field(payload, "locale"), LOCALES, "locale"))


def parse_turn(event_id: UUID, payload: Payload) -> TurnClassified:
    reply_ok = require_bool(field(payload, "reply_ok"), "reply_ok")
    reason_code = field(payload, "reason_code")
    if not reply_ok:
        return WithheldTurn(event_id, parse_withheld_reason(reason_code))
    if reason_code is not None:
        raise ValueError(f"a shown turn has no reason_code, got {reason_code!r}")
    return ShownTurn(
        event_id,
        intent=parse_member(field(payload, "intent"), INTENTS, "intent"),
        product=parse_optional_product(field(payload, "product")),
        language=parse_member(field(payload, "language"), TURN_LANGUAGES, "language"),
        declared_income_amount=parse_amount(field(payload, "declared_income_amount")),
        declared_income_currency=parse_optional_currency(field(payload, "declared_income_currency")),
        product_asked_count=parse_count(field(payload, "product_asked_count")),
        income_requested=require_bool(field(payload, "income_requested"), "income_requested"),
    )


def parse_withheld_reason(value: object) -> ReasonCode:
    reason = parse_member(value, REASON_CODES, "reason_code")
    if reason not in WITHHELD_REASONS:
        raise ValueError(f"a withheld turn is {' or '.join(sorted(WITHHELD_REASONS))}, not {reason}")
    return reason


def parse_close_outcome(payload: Payload) -> CloseOutcome:
    return parse_member(field(payload, "outcome"), CLOSE_OUTCOMES, "outcome")


def parse_optional_product(value: object) -> ProductKey | None:
    return None if value is None else parse_member(value, PRODUCT_KEYS, "product")


def parse_optional_currency(value: object) -> IncomeCurrency | None:
    return None if value is None else parse_member(value, INCOME_CURRENCIES, "declared_income_currency")


def parse_amount(value: object) -> Decimal | None:
    if value is None:
        return None
    if type(value) is int:
        value = Decimal(value)
    if type(value) is not Decimal:
        raise TypeError(f"declared_income_amount must be read as Decimal, got {type(value).__name__}")
    if not value.is_finite() or value < 0:
        raise ValueError(f"declared_income_amount {value} is not an income")
    return value


def parse_count(value: object) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"product_asked_count must be a whole number of asks, got {value!r}")
    return value


def require_bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise TypeError(f"{label} must be a boolean, got {value!r}")
    return value


def field(payload: Payload, name: str) -> object:
    if name not in payload:
        raise ValueError(f"payload has no {name}")
    return payload[name]
