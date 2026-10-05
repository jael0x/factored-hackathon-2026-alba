from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, assert_never, get_args

from api.contract_models import (
    DecidedBy,
    EndReason,
    IncomeCurrency,
    Locale,
    ProcessState,
    ProductKey,
    ReasonCode,
    TemplateId,
)
from api.domain.closed_sets import parse_member
from api.domain.json_value import Payload
from api.domain.locale import LOCALES
from api.domain.process.lifecycle import END_REASONS, HUMAN_ACTIVE, PROCESS_STATES, REASON_CODES
from api.domain.process.stored_events import (
    DECIDED_BY,
    PRODUCT_KEYS,
    TEMPLATE_IDS,
    field,
    parse_amount,
    parse_optional_currency,
)

CommandName = Literal[
    "process.start",
    "process.transition",
    "process.end",
    "conversation.generate",
    "conversation.show_reply",
    "template.send",
    "policy.run",
    "decision.render",
]

PROCESS_START: CommandName = "process.start"
PROCESS_TRANSITION: CommandName = "process.transition"
PROCESS_END: CommandName = "process.end"
CONVERSATION_GENERATE: CommandName = "conversation.generate"
CONVERSATION_SHOW_REPLY: CommandName = "conversation.show_reply"
TEMPLATE_SEND: CommandName = "template.send"
POLICY_RUN: CommandName = "policy.run"
DECISION_RENDER: CommandName = "decision.render"
COMMAND_NAMES: frozenset[CommandName] = frozenset(get_args(CommandName))

CommandStatus = Literal["pending", "done", "failed"]

PENDING: CommandStatus = "pending"
DONE: CommandStatus = "done"
FAILED: CommandStatus = "failed"

MAX_ATTEMPTS = 3

NEEDS_INCOME: TemplateId = "needs_income"
REFER_NOTICE: TemplateId = "refer_notice"
WHICH_PRODUCT: TemplateId = "which_product"
CONFIRM_PREQUALIFY_TEMPLATE: TemplateId = "confirm_prequalify"
PRODUCT_CASE_OPEN: TemplateId = "product_case_open"

DECIDED_BY_POLICY: DecidedBy = "policy"
DECIDED_BY_CONSULTANT: DecidedBy = "consultant"


@dataclass(frozen=True)
class NoPayload:
    pass


@dataclass(frozen=True)
class StartPayload:
    locale: Locale
    product: ProductKey


@dataclass(frozen=True)
class TemplatePayload:
    template_id: TemplateId


@dataclass(frozen=True)
class PolicyRunPayload:
    product: ProductKey
    declared_income_amount: Decimal | None
    declared_income_currency: IncomeCurrency | None


@dataclass(frozen=True)
class TransitionPayload:
    to_state: ProcessState
    reason_code: ReasonCode


@dataclass(frozen=True)
class RenderPayload:
    decided_by: DecidedBy


@dataclass(frozen=True)
class EndPayload:
    end_reason: EndReason


CommandPayload = (
    NoPayload | StartPayload | TemplatePayload | PolicyRunPayload | TransitionPayload | RenderPayload | EndPayload
)


@dataclass(frozen=True)
class Command:
    command_name: CommandName
    payload: CommandPayload


GENERATE_COMMAND = Command(CONVERSATION_GENERATE, NoPayload())
SHOW_REPLY_COMMAND = Command(CONVERSATION_SHOW_REPLY, NoPayload())


def start_process(locale: Locale, product: ProductKey) -> Command:
    return Command(PROCESS_START, StartPayload(locale, product))


def send_template(template_id: TemplateId) -> Command:
    return Command(TEMPLATE_SEND, TemplatePayload(template_id))


def run_policy(
    product: ProductKey, declared_income_amount: Decimal | None, declared_income_currency: IncomeCurrency | None
) -> Command:
    return Command(POLICY_RUN, PolicyRunPayload(product, declared_income_amount, declared_income_currency))


def hand_off(reason_code: ReasonCode) -> Command:
    return Command(PROCESS_TRANSITION, TransitionPayload(HUMAN_ACTIVE, reason_code))


def render_decision(decided_by: DecidedBy) -> Command:
    return Command(DECISION_RENDER, RenderPayload(decided_by))


def end_process(end_reason: EndReason) -> Command:
    return Command(PROCESS_END, EndPayload(end_reason))


def command_payload(payload: CommandPayload) -> Payload:
    match payload:
        case NoPayload():
            return {}
        case StartPayload():
            return {"locale": payload.locale, "product": payload.product}
        case TemplatePayload():
            return {"template_id": payload.template_id}
        case PolicyRunPayload():
            return {
                "product": payload.product,
                "declared_income_amount": payload.declared_income_amount,
                "declared_income_currency": payload.declared_income_currency,
            }
        case TransitionPayload():
            return {"to_state": payload.to_state, "reason_code": payload.reason_code}
        case RenderPayload():
            return {"decided_by": payload.decided_by}
        case EndPayload():
            return {"end_reason": payload.end_reason}
        case _:
            assert_never(payload)


def parse_command(command_name: object, payload: Mapping[str, object]) -> Command:
    name = parse_member(command_name, COMMAND_NAMES, "command name")
    return Command(name, parse_payload(name, payload))


def parse_payload(name: CommandName, payload: Mapping[str, object]) -> CommandPayload:
    if name in (CONVERSATION_GENERATE, CONVERSATION_SHOW_REPLY):
        if payload:
            raise ValueError(f"{name} takes no payload, got {sorted(payload)}")
        return NoPayload()
    if name == PROCESS_START:
        return StartPayload(
            parse_member(field(payload, "locale"), LOCALES, "locale"),
            parse_member(field(payload, "product"), PRODUCT_KEYS, "product"),
        )
    if name == TEMPLATE_SEND:
        return TemplatePayload(parse_member(field(payload, "template_id"), TEMPLATE_IDS, "template_id"))
    if name == POLICY_RUN:
        return PolicyRunPayload(
            product=parse_member(field(payload, "product"), PRODUCT_KEYS, "product"),
            declared_income_amount=parse_amount(field(payload, "declared_income_amount")),
            declared_income_currency=parse_optional_currency(field(payload, "declared_income_currency")),
        )
    if name == PROCESS_TRANSITION:
        return TransitionPayload(
            to_state=parse_member(field(payload, "to_state"), PROCESS_STATES, "to_state"),
            reason_code=parse_member(field(payload, "reason_code"), REASON_CODES, "reason_code"),
        )
    if name == DECISION_RENDER:
        return RenderPayload(parse_member(field(payload, "decided_by"), DECIDED_BY, "decided_by"))
    return EndPayload(parse_member(field(payload, "end_reason"), END_REASONS, "end_reason"))
