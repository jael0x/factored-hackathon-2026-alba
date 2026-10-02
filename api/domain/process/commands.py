from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, get_args

from api.contract_models import DecidedBy, EndReason, IncomeCurrency, ProcessState, ProductKey, ReasonCode, TemplateId
from api.domain.process.lifecycle import HUMAN_ACTIVE

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

NEEDS_INCOME: TemplateId = "needs_income"
REFER_NOTICE: TemplateId = "refer_notice"
WHICH_PRODUCT: TemplateId = "which_product"
CONFIRM_PREQUALIFY_TEMPLATE: TemplateId = "confirm_prequalify"

DECIDED_BY_POLICY: DecidedBy = "policy"
DECIDED_BY_CONSULTANT: DecidedBy = "consultant"


@dataclass(frozen=True)
class NoPayload:
    pass


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


CommandPayload = NoPayload | TemplatePayload | PolicyRunPayload | TransitionPayload | RenderPayload | EndPayload


@dataclass(frozen=True)
class Command:
    command_name: CommandName
    payload: CommandPayload


START_COMMAND = Command(PROCESS_START, NoPayload())
GENERATE_COMMAND = Command(CONVERSATION_GENERATE, NoPayload())
SHOW_REPLY_COMMAND = Command(CONVERSATION_SHOW_REPLY, NoPayload())


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
