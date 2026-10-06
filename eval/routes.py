from dataclasses import dataclass
from uuid import UUID

from api.contract_models import ProductKey
from api.domain.process.commands import PolicyRunPayload
from api.domain.process.lifecycle import AI_ACTIVE, ProcessRow
from api.domain.process.new_events import Cause, turn_classified
from api.domain.process.rules import (
    HAND_OFF_HUMAN,
    HAND_OFF_LANGUAGE,
    HAND_OFF_NO_PRODUCT,
    HAND_OFF_REPLY,
    HAND_OFF_SCOPE,
    RUN_POLICY,
    RUN_POLICY_INCOME,
    ProcessRuleId,
    match_rules,
)
from api.domain.process.stored_events import parse_stored_event
from api.domain.process.turns import ModelReading, ShownReading, TurnReading, TurnStamp
from eval.heldout import HeldOutItem

PROCESS_ID = UUID("11111111-1111-4111-8111-111111111111")
MESSAGE_ID = UUID("22222222-2222-4222-8222-222222222222")
COMMAND_ID = UUID("33333333-3333-4333-8333-333333333333")
TURN_ID = UUID("44444444-4444-4444-8444-444444444444")
POLICY_RULES: frozenset[ProcessRuleId] = frozenset({RUN_POLICY, RUN_POLICY_INCOME})
HANDOFF_RULES: frozenset[ProcessRuleId] = frozenset(
    {HAND_OFF_NO_PRODUCT, HAND_OFF_HUMAN, HAND_OFF_SCOPE, HAND_OFF_LANGUAGE, HAND_OFF_REPLY}
)


# What the engine does next with a turn: the rules that fire on it, or a failed read, which the worker's third
# attempt sends to a person with tool_failed.
@dataclass(frozen=True)
class Route:
    rules: tuple[ProcessRuleId, ...]
    policy_product: ProductKey | None
    failed: bool = False

    @property
    def runs_policy(self) -> bool:
        return bool(POLICY_RULES & set(self.rules))

    @property
    def hands_off(self) -> bool:
        return self.failed or bool(HANDOFF_RULES & set(self.rules))


FAILED_READ = Route(rules=(), policy_product=None, failed=True)


def expected_reading(item: HeldOutItem) -> ModelReading:
    gold = item.expected
    reading = TurnReading(
        gold.intent, gold.product, gold.language, gold.declared_income_amount, gold.declared_income_currency, ""
    )
    return ShownReading(reading)


# The stamp mirrors stamp_turn on a case whose history the item's context summarizes: the stored product unless the
# turn names one, and the income request only while the product stays the one it was asked for.
def route_of(model: ModelReading, item: HeldOutItem) -> Route:
    context = item.context
    product = context.stored_product if model.reading.product is None else model.reading.product
    stamp = TurnStamp(product, context.asked, context.income_requested and product == context.stored_product)
    process = ProcessRow(PROCESS_ID, "CLI-EVAL", AI_ACTIVE)
    event = turn_classified(process, item.locale, model, stamp, Cause(MESSAGE_ID, COMMAND_ID))
    stored = parse_stored_event(TURN_ID, event.event_name, event.process_id, event.process_state, event.payload)
    planned = match_rules(stored)
    runs = [p.command.payload for p in planned if isinstance(p.command.payload, PolicyRunPayload)]
    return Route(
        rules=tuple(p.emitted_by_rule_id for p in planned),
        policy_product=runs[0].product if runs else None,
    )
