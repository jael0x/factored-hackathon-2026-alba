from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Generic, Literal, TypeVar, assert_never, get_args
from uuid import UUID

from api.contract_models import EndReason, EventName, Intent, Outcome, ProcessState
from api.domain.policy.engine import NEEDS_INFO, NOT_PREQUALIFIED, PREQUALIFIED, REFER
from api.domain.process.commands import (
    CONFIRM_PREQUALIFY_TEMPLATE,
    DECIDED_BY_CONSULTANT,
    DECIDED_BY_POLICY,
    GENERATE_COMMAND,
    NEEDS_INCOME,
    REFER_NOTICE,
    SHOW_REPLY_COMMAND,
    WHICH_PRODUCT,
    Command,
    CommandName,
    end_process,
    hand_off,
    render_decision,
    run_policy,
    send_template,
    start_process,
)
from api.domain.process.events import (
    ANALYSIS_COMPLETED,
    CONSULTANT_CLOSED,
    MESSAGE_RECEIVED,
    PREQUALIFICATION_DECIDED,
    TURN_CLASSIFIED,
)
from api.domain.process.lifecycle import (
    AI_ACTIVE,
    CUSTOMER_REQUESTED_HUMAN,
    HUMAN_ACTIVE,
    LANGUAGE_UNSUPPORTED,
    NOT_PREQUALIFIED_END,
    OUT_OF_SCOPE,
    POLICY_REFER,
    PREQUALIFIED_END,
)
from api.domain.process.stored_events import (
    CHIT_CHAT_INTENT,
    CLARIFY_INTENT,
    CLOSE_OUTCOMES,
    CONFIRM_PREQUALIFY_INTENT,
    DECLINE_PREQUALIFY_INTENT,
    HUMAN_REQUEST_INTENT,
    OTHER_LANGUAGE,
    OUT_OF_SCOPE_INTENT,
    PREQUALIFY_CARD_INTENT,
    PREQUALIFY_LOAN_INTENT,
    PRODUCT_INFO_INTENT,
    PROVIDE_INCOME_INTENT,
    TEMPLATE_LANGUAGES,
    AnalysisCompleted,
    ConsultantClosed,
    MessageReceived,
    NoRuleEvent,
    PrequalificationDecided,
    ShownTurn,
    StoredEvent,
    TurnClassified,
    WithheldTurn,
)

ProcessRuleId = Literal[
    "open_process",
    "generate_while_ai",
    "record_only_when_human",
    "ask_confirm_prequalify",
    "run_policy",
    "decline_prequalify",
    "run_policy_income",
    "ask_consent_for_income",
    "ask_which_product",
    "hand_off_no_product",
    "hand_off_human",
    "hand_off_scope",
    "hand_off_language",
    "hand_off_reply",
    "show_reply",
    "render_needs_info",
    "render_refer_notice",
    "take_thread",
    "render_decision",
    "end_after_decision",
    "close_on_consultant_decision",
]

OPEN_PROCESS: ProcessRuleId = "open_process"
GENERATE_WHILE_AI: ProcessRuleId = "generate_while_ai"
RECORD_ONLY_WHEN_HUMAN: ProcessRuleId = "record_only_when_human"
ASK_CONFIRM_PREQUALIFY: ProcessRuleId = "ask_confirm_prequalify"
RUN_POLICY: ProcessRuleId = "run_policy"
DECLINE_PREQUALIFY: ProcessRuleId = "decline_prequalify"
RUN_POLICY_INCOME: ProcessRuleId = "run_policy_income"
ASK_CONSENT_FOR_INCOME: ProcessRuleId = "ask_consent_for_income"
ASK_WHICH_PRODUCT: ProcessRuleId = "ask_which_product"
HAND_OFF_NO_PRODUCT: ProcessRuleId = "hand_off_no_product"
HAND_OFF_HUMAN: ProcessRuleId = "hand_off_human"
HAND_OFF_SCOPE: ProcessRuleId = "hand_off_scope"
HAND_OFF_LANGUAGE: ProcessRuleId = "hand_off_language"
HAND_OFF_REPLY: ProcessRuleId = "hand_off_reply"
SHOW_REPLY: ProcessRuleId = "show_reply"
RENDER_NEEDS_INFO: ProcessRuleId = "render_needs_info"
RENDER_REFER_NOTICE: ProcessRuleId = "render_refer_notice"
TAKE_THREAD: ProcessRuleId = "take_thread"
RENDER_DECISION: ProcessRuleId = "render_decision"
END_AFTER_DECISION: ProcessRuleId = "end_after_decision"
CLOSE_ON_CONSULTANT_DECISION: ProcessRuleId = "close_on_consultant_decision"
PROCESS_RULE_IDS: frozenset[ProcessRuleId] = frozenset(get_args(ProcessRuleId))

PRODUCT_ASKS_BEFORE_HANDOFF = 2

END_REASON_BY_OUTCOME: Mapping[Outcome, EndReason] = MappingProxyType(
    {PREQUALIFIED: PREQUALIFIED_END, NOT_PREQUALIFIED: NOT_PREQUALIFIED_END}
)

Event = TypeVar("Event")


@dataclass(frozen=True)
class Rule(Generic[Event]):
    rule_id: ProcessRuleId
    trigger: EventName
    when: Callable[[Event], bool]
    actions: Callable[[Event], tuple[Command, ...]]


@dataclass(frozen=True)
class Firing:
    rule_id: ProcessRuleId
    commands: tuple[Command, ...]


@dataclass(frozen=True)
class PlannedCommand:
    command: Command
    emitted_by_rule_id: ProcessRuleId
    triggered_by_event_id: UUID
    idempotency_key: str


def command_key(rule_id: ProcessRuleId, command_name: CommandName, triggered_by_event_id: UUID) -> str:
    return f"command:{rule_id}:{command_name}:{triggered_by_event_id}"


def emits(*commands: Command) -> Callable[[object], tuple[Command, ...]]:
    def actions(_event: object) -> tuple[Command, ...]:
        return commands

    return actions


def opens_no_process(message: MessageReceived) -> bool:
    return message.process_id is None


def start_in_message_locale(message: MessageReceived) -> tuple[Command, ...]:
    return (start_process(message.locale),)


def stamped(state: ProcessState) -> Callable[[MessageReceived], bool]:
    def when(message: MessageReceived) -> bool:
        return message.process_state == state

    return when


def answerable(*intents: Intent) -> Callable[[TurnClassified], bool]:
    def when(turn: TurnClassified) -> bool:
        return isinstance(turn, ShownTurn) and turn.language in TEMPLATE_LANGUAGES and turn.intent in intents

    return when


def all_of(*conditions: Callable[[TurnClassified], bool]) -> Callable[[TurnClassified], bool]:
    def when(turn: TurnClassified) -> bool:
        return all(condition(turn) for condition in conditions)

    return when


def has_product(turn: TurnClassified) -> bool:
    return isinstance(turn, ShownTurn) and turn.product is not None


def income_requested(turn: TurnClassified) -> bool:
    return isinstance(turn, ShownTurn) and turn.income_requested


def income_not_requested(turn: TurnClassified) -> bool:
    return isinstance(turn, ShownTurn) and not turn.income_requested


def out_of_product_asks(turn: TurnClassified) -> bool:
    return (
        isinstance(turn, ShownTurn) and turn.product is None and turn.product_asked_count >= PRODUCT_ASKS_BEFORE_HANDOFF
    )


def product_still_askable(turn: TurnClassified) -> bool:
    return (
        isinstance(turn, ShownTurn) and turn.product is None and turn.product_asked_count < PRODUCT_ASKS_BEFORE_HANDOFF
    )


def not_a_spent_clarify(turn: TurnClassified) -> bool:
    return not (isinstance(turn, ShownTurn) and turn.intent == CLARIFY_INTENT and out_of_product_asks(turn))


def speaks_other_language(turn: TurnClassified) -> bool:
    return isinstance(turn, ShownTurn) and turn.language == OTHER_LANGUAGE


def is_withheld(turn: TurnClassified) -> bool:
    return isinstance(turn, WithheldTurn)


def policy_run_from_turn(turn: TurnClassified) -> tuple[Command, ...]:
    if not isinstance(turn, ShownTurn) or turn.product is None:
        raise ValueError("policy.run needs a shown turn with a product")
    return (run_policy(turn.product, turn.declared_income_amount, turn.declared_income_currency),)


def hand_off_withheld(turn: TurnClassified) -> tuple[Command, ...]:
    if not isinstance(turn, WithheldTurn):
        raise ValueError("hand_off_reply needs a withheld turn")
    return (hand_off(turn.reason_code),)


def outcome_is(*outcomes: Outcome) -> Callable[[AnalysisCompleted], bool]:
    def when(analysis: AnalysisCompleted) -> bool:
        return analysis.outcome in outcomes

    return when


def decided_by_policy(decided: PrequalificationDecided) -> bool:
    return decided.decided_by == DECIDED_BY_POLICY


def end_for_decision(decided: PrequalificationDecided) -> tuple[Command, ...]:
    return (end_process(END_REASON_BY_OUTCOME[decided.outcome]),)


def is_close(closed: ConsultantClosed) -> bool:
    return closed.outcome in CLOSE_OUTCOMES


def close_for_consultant(closed: ConsultantClosed) -> tuple[Command, ...]:
    return (render_decision(DECIDED_BY_CONSULTANT), end_process(END_REASON_BY_OUTCOME[closed.outcome]))


MESSAGE_RULES: tuple[Rule[MessageReceived], ...] = (
    Rule(OPEN_PROCESS, MESSAGE_RECEIVED, opens_no_process, start_in_message_locale),
    Rule(GENERATE_WHILE_AI, MESSAGE_RECEIVED, stamped(AI_ACTIVE), emits(GENERATE_COMMAND)),
    Rule(RECORD_ONLY_WHEN_HUMAN, MESSAGE_RECEIVED, stamped(HUMAN_ACTIVE), emits()),
)

TURN_RULES: tuple[Rule[TurnClassified], ...] = (
    Rule(
        ASK_CONFIRM_PREQUALIFY,
        TURN_CLASSIFIED,
        answerable(PREQUALIFY_CARD_INTENT, PREQUALIFY_LOAN_INTENT),
        emits(send_template(CONFIRM_PREQUALIFY_TEMPLATE)),
    ),
    Rule(RUN_POLICY, TURN_CLASSIFIED, all_of(answerable(CONFIRM_PREQUALIFY_INTENT), has_product), policy_run_from_turn),
    Rule(DECLINE_PREQUALIFY, TURN_CLASSIFIED, answerable(DECLINE_PREQUALIFY_INTENT), emits(SHOW_REPLY_COMMAND)),
    Rule(
        RUN_POLICY_INCOME,
        TURN_CLASSIFIED,
        all_of(answerable(PROVIDE_INCOME_INTENT), has_product, income_requested),
        policy_run_from_turn,
    ),
    Rule(
        ASK_CONSENT_FOR_INCOME,
        TURN_CLASSIFIED,
        all_of(answerable(PROVIDE_INCOME_INTENT), has_product, income_not_requested),
        emits(send_template(CONFIRM_PREQUALIFY_TEMPLATE)),
    ),
    Rule(
        ASK_WHICH_PRODUCT,
        TURN_CLASSIFIED,
        all_of(answerable(PROVIDE_INCOME_INTENT, CONFIRM_PREQUALIFY_INTENT), product_still_askable),
        emits(send_template(WHICH_PRODUCT)),
    ),
    Rule(
        HAND_OFF_NO_PRODUCT,
        TURN_CLASSIFIED,
        all_of(answerable(CLARIFY_INTENT, PROVIDE_INCOME_INTENT, CONFIRM_PREQUALIFY_INTENT), out_of_product_asks),
        emits(hand_off(OUT_OF_SCOPE)),
    ),
    Rule(HAND_OFF_HUMAN, TURN_CLASSIFIED, answerable(HUMAN_REQUEST_INTENT), emits(hand_off(CUSTOMER_REQUESTED_HUMAN))),
    Rule(HAND_OFF_SCOPE, TURN_CLASSIFIED, answerable(OUT_OF_SCOPE_INTENT), emits(hand_off(OUT_OF_SCOPE))),
    Rule(HAND_OFF_LANGUAGE, TURN_CLASSIFIED, speaks_other_language, emits(hand_off(LANGUAGE_UNSUPPORTED))),
    Rule(HAND_OFF_REPLY, TURN_CLASSIFIED, is_withheld, hand_off_withheld),
    Rule(
        SHOW_REPLY,
        TURN_CLASSIFIED,
        all_of(answerable(CLARIFY_INTENT, PRODUCT_INFO_INTENT, CHIT_CHAT_INTENT), not_a_spent_clarify),
        emits(SHOW_REPLY_COMMAND),
    ),
)

ANALYSIS_RULES: tuple[Rule[AnalysisCompleted], ...] = (
    Rule(RENDER_NEEDS_INFO, ANALYSIS_COMPLETED, outcome_is(NEEDS_INFO), emits(send_template(NEEDS_INCOME))),
    Rule(RENDER_REFER_NOTICE, ANALYSIS_COMPLETED, outcome_is(REFER), emits(send_template(REFER_NOTICE))),
    Rule(TAKE_THREAD, ANALYSIS_COMPLETED, outcome_is(REFER), emits(hand_off(POLICY_REFER))),
    Rule(
        RENDER_DECISION,
        ANALYSIS_COMPLETED,
        outcome_is(PREQUALIFIED, NOT_PREQUALIFIED),
        emits(render_decision(DECIDED_BY_POLICY)),
    ),
)

DECIDED_RULES: tuple[Rule[PrequalificationDecided], ...] = (
    Rule(END_AFTER_DECISION, PREQUALIFICATION_DECIDED, decided_by_policy, end_for_decision),
)

CLOSE_RULES: tuple[Rule[ConsultantClosed], ...] = (
    Rule(CLOSE_ON_CONSULTANT_DECISION, CONSULTANT_CLOSED, is_close, close_for_consultant),
)


RuleTable = (
    tuple[Rule[MessageReceived], ...]
    | tuple[Rule[TurnClassified], ...]
    | tuple[Rule[AnalysisCompleted], ...]
    | tuple[Rule[PrequalificationDecided], ...]
    | tuple[Rule[ConsultantClosed], ...]
)


def fire(rules: tuple[Rule[Event], ...], event: Event) -> tuple[Firing, ...]:
    return tuple(Firing(rule.rule_id, distinct_commands(rule)(event)) for rule in rules if rule.when(event))


def distinct_commands(rule: Rule[Event]) -> Callable[[Event], tuple[Command, ...]]:
    def actions(event: Event) -> tuple[Command, ...]:
        commands = rule.actions(event)
        names = [command.command_name for command in commands]
        if len(names) != len(set(names)):
            raise ValueError(f"{rule.rule_id} emits a command twice, so their keys would collide")
        return commands

    return actions


def fired_rules(event: StoredEvent) -> tuple[Firing, ...]:
    match event:
        case MessageReceived():
            return fire(MESSAGE_RULES, event)
        case ShownTurn() | WithheldTurn():
            return fire(TURN_RULES, event)
        case AnalysisCompleted():
            return fire(ANALYSIS_RULES, event)
        case PrequalificationDecided():
            return fire(DECIDED_RULES, event)
        case ConsultantClosed():
            return fire(CLOSE_RULES, event)
        case NoRuleEvent():
            return ()
        case _:
            assert_never(event)


def matching_rules(event: StoredEvent) -> tuple[ProcessRuleId, ...]:
    return tuple(firing.rule_id for firing in fired_rules(event))


def match_rules(event: StoredEvent) -> tuple[PlannedCommand, ...]:
    return tuple(
        PlannedCommand(
            command=command,
            emitted_by_rule_id=firing.rule_id,
            triggered_by_event_id=event.event_id,
            idempotency_key=command_key(firing.rule_id, command.command_name, event.event_id),
        )
        for firing in fired_rules(event)
        for command in firing.commands
    )


def require_rule_table(tables: Mapping[EventName, RuleTable]) -> None:
    listed = [rule.rule_id for rules in tables.values() for rule in rules]
    if len(listed) != len(set(listed)):
        raise ValueError("a process rule is listed twice, so it would fire twice")
    if set(listed) != PROCESS_RULE_IDS:
        raise ValueError(f"process rules must list every rule id: {sorted(PROCESS_RULE_IDS - set(listed))}")
    misfiled = [rule.rule_id for trigger, rules in tables.items() for rule in rules if rule.trigger != trigger]
    if misfiled:
        raise ValueError(f"rules filed under another trigger: {misfiled}")


def require_end_reasons(end_reasons: Mapping[Outcome, EndReason]) -> None:
    if set(end_reasons) != CLOSE_OUTCOMES:
        raise ValueError("every close outcome needs exactly one end reason")


RULE_TABLES: Mapping[EventName, RuleTable] = MappingProxyType(
    {
        MESSAGE_RECEIVED: MESSAGE_RULES,
        TURN_CLASSIFIED: TURN_RULES,
        ANALYSIS_COMPLETED: ANALYSIS_RULES,
        PREQUALIFICATION_DECIDED: DECIDED_RULES,
        CONSULTANT_CLOSED: CLOSE_RULES,
    }
)

require_rule_table(RULE_TABLES)
require_end_reasons(END_REASON_BY_OUTCOME)
