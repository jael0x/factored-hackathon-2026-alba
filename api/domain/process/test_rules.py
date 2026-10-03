import itertools
from collections.abc import Mapping
from dataclasses import replace
from decimal import Decimal
from types import MappingProxyType
from typing import get_args
from uuid import UUID

import pytest

from api.contract_models import EndReason, EventName, Intent, ProductKey, TurnLanguage
from api.domain.process.commands import (
    GENERATE_COMMAND,
    SHOW_REPLY_COMMAND,
    START_COMMAND,
    Command,
    end_process,
    hand_off,
    render_decision,
    run_policy,
    send_template,
)
from api.domain.process.rules import (
    ANALYSIS_RULES,
    CLOSE_RULES,
    DECIDED_RULES,
    END_REASON_BY_OUTCOME,
    MESSAGE_RULES,
    RULE_TABLES,
    TURN_RULES,
    PlannedCommand,
    ProcessRuleId,
    Rule,
    RuleTable,
    command_key,
    fire,
    hand_off_withheld,
    match_rules,
    matching_rules,
    policy_run_from_turn,
    require_end_reasons,
    require_rule_table,
)
from api.domain.process.stored_events import (
    MessageReceived,
    ShownTurn,
    StoredEvent,
    WithheldTurn,
    parse_stored_event,
)

EVENT_ID = UUID("33333333-3333-4333-8333-333333333333")
PROCESS_ID = UUID("11111111-1111-4111-8111-111111111111")
COUNTS = (0, 1, 2, 3)

Fired = tuple[tuple[ProcessRuleId, Command], ...]


def stored(event_name: str, payload: Mapping[str, object], process_id: UUID | None = PROCESS_ID) -> StoredEvent:
    return parse_stored_event(EVENT_ID, event_name, process_id, "ai_active", payload)


def message(process_id: UUID | None, state: str) -> StoredEvent:
    return parse_stored_event(EVENT_ID, "conversation.message_received", process_id, state, {})


def turn(**overrides: object) -> StoredEvent:
    payload: dict[str, object] = {
        "intent": "clarify",
        "product": None,
        "language": "es",
        "declared_income_amount": None,
        "declared_income_currency": None,
        "reply_text": "",
        "reply_ok": True,
        "reason_code": None,
        "product_asked_count": 0,
        "income_requested": False,
        **overrides,
    }
    return stored("conversation.turn_classified", payload)


def analysis(outcome: str) -> StoredEvent:
    return stored("analysis.completed", {"outcome": outcome})


def decided(outcome: str, decided_by: str) -> StoredEvent:
    return stored("prequalification.decided", {"outcome": outcome, "decided_by": decided_by})


def closed(outcome: str) -> StoredEvent:
    return stored("conversation.consultant_closed", {"outcome": outcome})


def fired(event: StoredEvent) -> Fired:
    return tuple((planned.emitted_by_rule_id, planned.command) for planned in match_rules(event))


def test_the_command_key_names_the_rule_the_command_and_the_event() -> None:
    assert command_key("run_policy", "policy.run", EVENT_ID) == f"command:run_policy:policy.run:{EVENT_ID}"


def test_a_planned_command_carries_its_rule_event_and_key() -> None:
    assert match_rules(turn(intent="confirm_prequalify", product="credit_card")) == (
        PlannedCommand(
            command=run_policy("credit_card", None, None),
            emitted_by_rule_id="run_policy",
            triggered_by_event_id=EVENT_ID,
            idempotency_key=f"command:run_policy:policy.run:{EVENT_ID}",
        ),
    )


def test_the_first_message_opens_the_case_then_classifies_it() -> None:
    assert fired(message(None, "ai_active")) == (
        ("open_process", START_COMMAND),
        ("generate_while_ai", GENERATE_COMMAND),
    )


def test_a_message_in_an_open_assistant_case_is_classified_only() -> None:
    assert fired(message(PROCESS_ID, "ai_active")) == (("generate_while_ai", GENERATE_COMMAND),)


def test_a_message_while_a_person_has_the_case_is_recorded_and_does_not_call_the_model() -> None:
    event = message(PROCESS_ID, "human_active")
    assert matching_rules(event) == ("record_only_when_human",)
    assert match_rules(event) == ()


TURN_CASES: list[tuple[str, StoredEvent, Fired]] = [
    (
        "a card request asks for consent",
        turn(intent="prequalify_card", product="credit_card"),
        (("ask_confirm_prequalify", send_template("confirm_prequalify")),),
    ),
    (
        "a loan request in Portuguese asks for consent",
        turn(intent="prequalify_loan", product="personal_loan", language="pt"),
        (("ask_confirm_prequalify", send_template("confirm_prequalify")),),
    ),
    (
        "a yes with a product runs the policy",
        turn(intent="confirm_prequalify", product="credit_card"),
        (("run_policy", run_policy("credit_card", None, None)),),
    ),
    (
        "a yes with an income runs the policy with that amount",
        turn(
            intent="confirm_prequalify",
            product="credit_card",
            declared_income_amount=Decimal("45000"),
            declared_income_currency="MXN",
        ),
        (("run_policy", run_policy("credit_card", Decimal("45000"), "MXN")),),
    ),
    (
        "a no shows the reply",
        turn(intent="decline_prequalify", product="credit_card"),
        (("decline_prequalify", SHOW_REPLY_COMMAND),),
    ),
    (
        "an income that was asked for runs the policy",
        turn(
            intent="provide_income",
            product="credit_card",
            income_requested=True,
            declared_income_amount=Decimal("45000"),
            declared_income_currency="MXN",
        ),
        (("run_policy_income", run_policy("credit_card", Decimal("45000"), "MXN")),),
    ),
    (
        "an income before consent asks for consent and drops the amount",
        turn(
            intent="provide_income",
            product="credit_card",
            declared_income_amount=Decimal("45000"),
            declared_income_currency="MXN",
        ),
        (("ask_consent_for_income", send_template("confirm_prequalify")),),
    ),
    (
        "a yes with no product, first ask",
        turn(intent="confirm_prequalify", product_asked_count=0),
        (("ask_which_product", send_template("which_product")),),
    ),
    (
        "an income with no product, second ask",
        turn(intent="provide_income", product_asked_count=1),
        (("ask_which_product", send_template("which_product")),),
    ),
    (
        "a yes with no product after two asks goes to a person",
        turn(intent="confirm_prequalify", product_asked_count=2),
        (("hand_off_no_product", hand_off("out_of_scope")),),
    ),
    (
        "an income with no product after three asks goes to a person",
        turn(intent="provide_income", product_asked_count=3),
        (("hand_off_no_product", hand_off("out_of_scope")),),
    ),
    (
        "a vague request is clarified the first time",
        turn(intent="clarify", product_asked_count=0),
        (("show_reply", SHOW_REPLY_COMMAND),),
    ),
    (
        "a vague request is clarified the second time",
        turn(intent="clarify", product_asked_count=1),
        (("show_reply", SHOW_REPLY_COMMAND),),
    ),
    (
        "a third vague request goes to a person",
        turn(intent="clarify", product_asked_count=2),
        (("hand_off_no_product", hand_off("out_of_scope")),),
    ),
    (
        "a clarification on a known product is shown however often it was asked",
        turn(intent="clarify", product="personal_loan", product_asked_count=5),
        (("show_reply", SHOW_REPLY_COMMAND),),
    ),
    (
        "a request for a person goes to a person",
        turn(intent="human_request"),
        (("hand_off_human", hand_off("customer_requested_human")),),
    ),
    (
        "an out of scope request goes to a person",
        turn(intent="out_of_scope"),
        (("hand_off_scope", hand_off("out_of_scope")),),
    ),
    (
        "another language with no product goes to a person, not to the product question",
        turn(intent="provide_income", language="other"),
        (("hand_off_language", hand_off("language_unsupported")),),
    ),
    (
        "another language goes to a person even with a card request",
        turn(intent="prequalify_card", product="credit_card", language="other"),
        (("hand_off_language", hand_off("language_unsupported")),),
    ),
    (
        "a forbidden reply goes to a person",
        turn(reply_ok=False, reason_code="reply_forbidden", intent="confirm_prequalify", product="credit_card"),
        (("hand_off_reply", hand_off("reply_forbidden")),),
    ),
    (
        "two invalid model outputs go to a person",
        turn(reply_ok=False, reason_code="model_output_invalid", language="other"),
        (("hand_off_reply", hand_off("model_output_invalid")),),
    ),
    (
        "a product question shows the reply",
        turn(intent="product_info", product="credit_card"),
        (("show_reply", SHOW_REPLY_COMMAND),),
    ),
    (
        "small talk shows the reply",
        turn(intent="chit_chat"),
        (("show_reply", SHOW_REPLY_COMMAND),),
    ),
]


@pytest.mark.parametrize(("event", "expected"), [case[1:] for case in TURN_CASES], ids=[c[0] for c in TURN_CASES])
def test_a_classified_turn_fires_its_rule(event: StoredEvent, expected: Fired) -> None:
    assert fired(event) == expected


NOT_FIRED: list[tuple[str, StoredEvent, ProcessRuleId]] = [
    (
        "consent is not asked in another language",
        turn(intent="prequalify_card", language="other"),
        "ask_confirm_prequalify",
    ),
    ("a yes with no product does not run the policy", turn(intent="confirm_prequalify"), "run_policy"),
    (
        "an income before consent does not run the policy",
        turn(intent="provide_income", product="credit_card"),
        "run_policy_income",
    ),
    (
        "an income that was asked for does not ask consent again",
        turn(intent="provide_income", product="credit_card", income_requested=True),
        "ask_consent_for_income",
    ),
    ("the third ask goes to a person", turn(intent="provide_income", product_asked_count=2), "ask_which_product"),
    ("the second ask is not a handoff", turn(intent="clarify", product_asked_count=1), "hand_off_no_product"),
    (
        "a known product is not a handoff",
        turn(intent="confirm_prequalify", product="credit_card", product_asked_count=2),
        "hand_off_no_product",
    ),
    ("a withheld turn is not shown", turn(reply_ok=False, reason_code="reply_forbidden"), "show_reply"),
    ("a shown turn is not a reply handoff", turn(intent="chit_chat"), "hand_off_reply"),
    ("Spanish is not another language", turn(intent="chit_chat"), "hand_off_language"),
    ("a spent clarify is not shown", turn(intent="clarify", product_asked_count=2), "show_reply"),
]


@pytest.mark.parametrize(("event", "rule_id"), [case[1:] for case in NOT_FIRED], ids=[c[0] for c in NOT_FIRED])
def test_a_rule_does_not_fire_outside_its_condition(event: StoredEvent, rule_id: ProcessRuleId) -> None:
    assert rule_id not in matching_rules(event)


EVERY_TURN = list(
    itertools.product(
        (True, False),
        get_args(TurnLanguage),
        get_args(Intent),
        (None, *get_args(ProductKey)),
        COUNTS,
        (True, False),
    )
)


def every_turn() -> list[StoredEvent]:
    return [
        turn(
            reply_ok=reply_ok,
            reason_code=None if reply_ok else "model_output_invalid",
            language=language,
            intent=intent,
            product=product,
            product_asked_count=count,
            income_requested=requested,
        )
        for reply_ok, language, intent, product, count, requested in EVERY_TURN
    ]


def test_every_classified_turn_matches_exactly_one_rule() -> None:
    assert len(EVERY_TURN) == 1440
    matches = [matching_rules(event) for event in every_turn()]
    assert [match for match in matches if len(match) != 1] == []
    assert {match[0] for match in matches} == {rule.rule_id for rule in TURN_RULES}


def test_matching_the_same_event_again_plans_the_same_keys() -> None:
    for event in every_turn():
        keys = [planned.idempotency_key for planned in match_rules(event)]
        assert keys == [planned.idempotency_key for planned in match_rules(event)]
        assert len(keys) == len(set(keys))


def test_needs_info_asks_for_income() -> None:
    assert fired(analysis("NEEDS_INFO")) == (("render_needs_info", send_template("needs_income")),)


def test_refer_sends_the_notice_then_hands_the_case_to_a_person() -> None:
    assert fired(analysis("REFER")) == (
        ("render_refer_notice", send_template("refer_notice")),
        ("take_thread", hand_off("policy_refer")),
    )


@pytest.mark.parametrize("outcome", ["PREQUALIFIED", "NOT_PREQUALIFIED"])
def test_a_final_policy_outcome_renders_the_certificate(outcome: str) -> None:
    assert fired(analysis(outcome)) == (("render_decision", render_decision("policy")),)


@pytest.mark.parametrize(
    ("outcome", "end_reason"), [("PREQUALIFIED", "prequalified"), ("NOT_PREQUALIFIED", "not_prequalified")]
)
def test_a_policy_certificate_ends_the_case_with_its_outcome(outcome: str, end_reason: EndReason) -> None:
    assert fired(decided(outcome, "policy")) == (("end_after_decision", end_process(end_reason)),)


@pytest.mark.parametrize("outcome", ["PREQUALIFIED", "NOT_PREQUALIFIED"])
def test_a_consultant_certificate_does_not_end_the_case_a_second_time(outcome: str) -> None:
    event = decided(outcome, "consultant")
    assert matching_rules(event) == ()
    assert match_rules(event) == ()


@pytest.mark.parametrize(
    ("outcome", "end_reason"), [("PREQUALIFIED", "prequalified"), ("NOT_PREQUALIFIED", "not_prequalified")]
)
def test_a_consultant_close_renders_then_ends_without_the_policy(outcome: str, end_reason: EndReason) -> None:
    assert fired(closed(outcome)) == (
        ("close_on_consultant_decision", render_decision("consultant")),
        ("close_on_consultant_decision", end_process(end_reason)),
    )


@pytest.mark.parametrize(
    "event_name",
    [
        "conversation.template_sent",
        "conversation.thread_taken",
        "process.started",
        "process.state_changed",
        "process.ended",
    ],
)
def test_an_event_no_rule_reads_plans_nothing(event_name: str) -> None:
    assert match_rules(stored(event_name, {})) == ()


def flow(events: list[StoredEvent]) -> list[Fired]:
    return [fired(event) for event in events]


def test_juan_prequalifies_for_a_card() -> None:
    assert flow(
        [
            message(None, "ai_active"),
            turn(intent="prequalify_card", product="credit_card"),
            turn(intent="confirm_prequalify", product="credit_card"),
            analysis("PREQUALIFIED"),
            decided("PREQUALIFIED", "policy"),
        ]
    ) == [
        (("open_process", START_COMMAND), ("generate_while_ai", GENERATE_COMMAND)),
        (("ask_confirm_prequalify", send_template("confirm_prequalify")),),
        (("run_policy", run_policy("credit_card", None, None)),),
        (("render_decision", render_decision("policy")),),
        (("end_after_decision", end_process("prequalified")),),
    ]


def test_juan_in_portuguese_takes_the_same_path() -> None:
    assert flow(
        [
            turn(intent="prequalify_card", product="credit_card", language="pt"),
            turn(intent="confirm_prequalify", product="credit_card", language="pt"),
        ]
    ) == [
        (("ask_confirm_prequalify", send_template("confirm_prequalify")),),
        (("run_policy", run_policy("credit_card", None, None)),),
    ]


def test_juliana_is_asked_for_income_then_decided_with_it() -> None:
    assert flow(
        [
            turn(intent="confirm_prequalify", product="credit_card"),
            analysis("NEEDS_INFO"),
            turn(
                intent="provide_income",
                product="credit_card",
                income_requested=True,
                declared_income_amount=Decimal("45000"),
                declared_income_currency="MXN",
            ),
            analysis("PREQUALIFIED"),
        ]
    ) == [
        (("run_policy", run_policy("credit_card", None, None)),),
        (("render_needs_info", send_template("needs_income")),),
        (("run_policy_income", run_policy("credit_card", Decimal("45000"), "MXN")),),
        (("render_decision", render_decision("policy")),),
    ]


def test_alicia_is_referred_waits_for_a_person_and_is_closed_by_one() -> None:
    assert flow(
        [
            turn(intent="confirm_prequalify", product="credit_card"),
            analysis("REFER"),
            message(PROCESS_ID, "human_active"),
            closed("PREQUALIFIED"),
        ]
    ) == [
        (("run_policy", run_policy("credit_card", None, None)),),
        (("render_refer_notice", send_template("refer_notice")), ("take_thread", hand_off("policy_refer"))),
        (),
        (
            ("close_on_consultant_decision", render_decision("consultant")),
            ("close_on_consultant_decision", end_process("prequalified")),
        ),
    ]


def test_mariana_does_not_prequalify_and_the_case_ends() -> None:
    assert flow(
        [
            turn(intent="confirm_prequalify", product="personal_loan"),
            analysis("NOT_PREQUALIFIED"),
            decided("NOT_PREQUALIFIED", "policy"),
        ]
    ) == [
        (("run_policy", run_policy("personal_loan", None, None)),),
        (("render_decision", render_decision("policy")),),
        (("end_after_decision", end_process("not_prequalified")),),
    ]


def tables_with(**changes: RuleTable) -> Mapping[EventName, RuleTable]:
    names: dict[str, EventName] = {
        "message": "conversation.message_received",
        "turn": "conversation.turn_classified",
        "analysis": "analysis.completed",
    }
    return MappingProxyType({**RULE_TABLES, **{names[key]: rules for key, rules in changes.items()}})


def test_the_rule_tables_list_every_rule_once_under_its_trigger() -> None:
    require_rule_table(RULE_TABLES)
    assert len([rule for rules in RULE_TABLES.values() for rule in rules]) == 21


def test_a_rule_listed_twice_is_refused() -> None:
    with pytest.raises(ValueError, match="listed twice"):
        require_rule_table(tables_with(message=(*MESSAGE_RULES, MESSAGE_RULES[0])))


def test_a_missing_rule_is_refused() -> None:
    with pytest.raises(ValueError, match=r"must list every rule id: \['generate_while_ai'\]"):
        require_rule_table(tables_with(message=(MESSAGE_RULES[0], MESSAGE_RULES[2])))


def test_a_rule_under_another_trigger_is_refused() -> None:
    misfiled = replace(ANALYSIS_RULES[0], trigger="conversation.turn_classified")
    with pytest.raises(ValueError, match=r"filed under another trigger: \['render_needs_info'\]"):
        require_rule_table(tables_with(analysis=(misfiled, *ANALYSIS_RULES[1:])))


def test_every_close_outcome_has_one_end_reason() -> None:
    require_end_reasons(END_REASON_BY_OUTCOME)
    with pytest.raises(ValueError, match="every close outcome needs exactly one end reason"):
        require_end_reasons(MappingProxyType({"PREQUALIFIED": "prequalified"}))


def test_a_rule_that_emits_a_command_twice_is_refused() -> None:
    twice: Rule[MessageReceived] = Rule(
        "open_process",
        "conversation.message_received",
        lambda _event: True,
        lambda _event: (START_COMMAND, START_COMMAND),
    )
    event = message(None, "ai_active")
    assert isinstance(event, MessageReceived)
    with pytest.raises(ValueError, match="open_process emits a command twice"):
        fire((twice,), event)


def test_policy_run_is_only_built_from_a_shown_turn_with_a_product() -> None:
    with pytest.raises(ValueError, match=r"policy\.run needs a shown turn with a product"):
        policy_run_from_turn(WithheldTurn(EVENT_ID, "reply_forbidden"))
    no_product = turn(intent="confirm_prequalify")
    assert isinstance(no_product, ShownTurn)
    with pytest.raises(ValueError, match=r"policy\.run needs a shown turn with a product"):
        policy_run_from_turn(no_product)


def test_a_reply_handoff_is_only_built_from_a_withheld_turn() -> None:
    shown = turn(intent="chit_chat")
    assert isinstance(shown, ShownTurn)
    with pytest.raises(ValueError, match="hand_off_reply needs a withheld turn"):
        hand_off_withheld(shown)


def test_no_trigger_table_is_shared() -> None:
    tables = (MESSAGE_RULES, TURN_RULES, ANALYSIS_RULES, DECIDED_RULES, CLOSE_RULES)
    assert tuple(RULE_TABLES.values()) == tables
