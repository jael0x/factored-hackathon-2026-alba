from decimal import Decimal
from uuid import UUID

import pytest

from api.contract_models import EventName, Outcome, ProcessState, ReasonCode
from api.domain.process.stored_events import (
    AnalysisCompleted,
    ConsultantClosed,
    MessageReceived,
    NoRuleEvent,
    Payload,
    PrequalificationDecided,
    ShownTurn,
    WithheldTurn,
    parse_stored_event,
)

EVENT_ID = UUID("22222222-2222-4222-8222-222222222222")
PROCESS_ID = UUID("11111111-1111-4111-8111-111111111111")


def turn_payload(**overrides: object) -> dict[str, object]:
    return {
        "intent": "confirm_prequalify",
        "product": "credit_card",
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


def parse_turn(payload: Payload) -> object:
    return parse_stored_event(EVENT_ID, "conversation.turn_classified", PROCESS_ID, "ai_active", payload)


def parse_message(process_id: UUID | None, state: str) -> object:
    return parse_stored_event(EVENT_ID, "conversation.message_received", process_id, state, {})


def test_a_first_message_has_no_process_and_the_birth_state() -> None:
    assert parse_message(None, "ai_active") == MessageReceived(EVENT_ID, None, "ai_active")


@pytest.mark.parametrize("state", ["ai_active", "human_active"])
def test_a_message_in_an_open_case_carries_its_state(state: ProcessState) -> None:
    assert parse_message(PROCESS_ID, state) == MessageReceived(EVENT_ID, PROCESS_ID, state)


@pytest.mark.parametrize(
    ("process_id", "state", "error"),
    [
        (None, "human_active", "a message with no process is stamped ai_active, not human_active"),
        (None, "ended", "never stamped with an ended process"),
        (PROCESS_ID, "ended", "never stamped with an ended process"),
        (PROCESS_ID, "started", "process state 'started' is not one of"),
    ],
)
def test_a_stamp_the_contract_cannot_produce_is_refused(process_id: UUID | None, state: str, error: str) -> None:
    with pytest.raises(ValueError, match=error):
        parse_message(process_id, state)


def test_a_shown_turn_reads_every_field_the_rules_match_on() -> None:
    payload = turn_payload(
        intent="provide_income",
        declared_income_amount=Decimal("45000.50"),
        declared_income_currency="MXN",
        product_asked_count=1,
        income_requested=True,
    )
    assert parse_turn(payload) == ShownTurn(
        EVENT_ID,
        intent="provide_income",
        product="credit_card",
        language="es",
        declared_income_amount=Decimal("45000.50"),
        declared_income_currency="MXN",
        product_asked_count=1,
        income_requested=True,
    )


def test_a_whole_amount_is_read_as_decimal() -> None:
    turn = parse_turn(turn_payload(declared_income_amount=45000, declared_income_currency="COP"))
    assert isinstance(turn, ShownTurn)
    assert turn.declared_income_amount == Decimal(45000)
    assert type(turn.declared_income_amount) is Decimal


def test_a_null_product_and_amount_stay_null() -> None:
    turn = parse_turn(turn_payload(product=None))
    assert isinstance(turn, ShownTurn)
    assert (turn.product, turn.declared_income_amount, turn.declared_income_currency) == (None, None, None)


def test_a_float_amount_is_refused_because_money_is_never_a_float() -> None:
    with pytest.raises(TypeError, match="must be read as Decimal, got float"):
        parse_turn(turn_payload(declared_income_amount=45000.5))


@pytest.mark.parametrize("amount", [Decimal("-1"), Decimal("NaN"), Decimal("Infinity")])
def test_an_amount_that_is_not_an_income_is_refused(amount: Decimal) -> None:
    with pytest.raises(ValueError, match="is not an income"):
        parse_turn(turn_payload(declared_income_amount=amount))


@pytest.mark.parametrize("reason", ["reply_forbidden", "model_output_invalid"])
def test_a_withheld_turn_keeps_only_its_reason(reason: ReasonCode) -> None:
    payload = turn_payload(reply_ok=False, reason_code=reason, intent=None, language=None)
    assert parse_turn(payload) == WithheldTurn(EVENT_ID, reason)


def test_a_withheld_turn_needs_a_reason() -> None:
    with pytest.raises(ValueError, match="reason_code None is not one of"):
        parse_turn(turn_payload(reply_ok=False, reason_code=None))


def test_a_withheld_turn_is_never_a_policy_reason() -> None:
    with pytest.raises(
        ValueError, match="a withheld turn is model_output_invalid or reply_forbidden, not policy_refer"
    ):
        parse_turn(turn_payload(reply_ok=False, reason_code="policy_refer"))


def test_a_shown_turn_has_no_reason() -> None:
    with pytest.raises(ValueError, match="a shown turn has no reason_code, got 'reply_forbidden'"):
        parse_turn(turn_payload(reason_code="reply_forbidden"))


@pytest.mark.parametrize("count", [-1, True, "2", None])
def test_a_count_that_is_not_a_whole_number_of_asks_is_refused(count: object) -> None:
    with pytest.raises(ValueError, match="product_asked_count must be a whole number of asks"):
        parse_turn(turn_payload(product_asked_count=count))


@pytest.mark.parametrize(("field", "value"), [("reply_ok", "true"), ("income_requested", 1)])
def test_a_flag_must_be_a_boolean(field: str, value: object) -> None:
    with pytest.raises(TypeError, match=f"{field} must be a boolean"):
        parse_turn(turn_payload(**{field: value}))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("intent", "mortgage"),
        ("product", "mortgage"),
        ("language", "fr"),
        ("declared_income_currency", "USD"),
    ],
)
def test_a_value_outside_its_closed_set_is_refused(field: str, value: str) -> None:
    with pytest.raises(ValueError, match=f"{value!r} is not one of"):
        parse_turn(turn_payload(**{field: value}))


def test_a_missing_field_is_named() -> None:
    payload = turn_payload()
    del payload["income_requested"]
    with pytest.raises(ValueError, match="payload has no income_requested"):
        parse_turn(payload)


@pytest.mark.parametrize("outcome", ["PREQUALIFIED", "NOT_PREQUALIFIED", "REFER", "NEEDS_INFO"])
def test_an_analysis_carries_its_outcome(outcome: Outcome) -> None:
    event = parse_stored_event(EVENT_ID, "analysis.completed", PROCESS_ID, "ai_active", {"outcome": outcome})
    assert event == AnalysisCompleted(EVENT_ID, outcome)


def test_a_decision_carries_its_outcome_and_who_decided() -> None:
    payload = {"outcome": "NOT_PREQUALIFIED", "decided_by": "consultant"}
    event = parse_stored_event(EVENT_ID, "prequalification.decided", PROCESS_ID, "human_active", payload)
    assert event == PrequalificationDecided(EVENT_ID, "NOT_PREQUALIFIED", "consultant")


@pytest.mark.parametrize("event_name", ["prequalification.decided", "conversation.consultant_closed"])
def test_a_decision_or_close_is_never_refer(event_name: str) -> None:
    payload = {"outcome": "REFER", "decided_by": "policy"}
    with pytest.raises(ValueError, match="outcome 'REFER' is not one of NOT_PREQUALIFIED, PREQUALIFIED"):
        parse_stored_event(EVENT_ID, event_name, PROCESS_ID, "human_active", payload)


def test_a_decision_by_someone_else_is_refused() -> None:
    payload = {"outcome": "PREQUALIFIED", "decided_by": "model"}
    with pytest.raises(ValueError, match="decided_by 'model' is not one of"):
        parse_stored_event(EVENT_ID, "prequalification.decided", PROCESS_ID, "ai_active", payload)


def test_a_close_carries_its_outcome() -> None:
    payload = {"outcome": "PREQUALIFIED", "consultant_id": "AGT-1", "language": "es"}
    event = parse_stored_event(EVENT_ID, "conversation.consultant_closed", PROCESS_ID, "human_active", payload)
    assert event == ConsultantClosed(EVENT_ID, "PREQUALIFIED")


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
def test_an_event_no_rule_reads_keeps_only_its_name(event_name: EventName) -> None:
    event = parse_stored_event(EVENT_ID, event_name, PROCESS_ID, "ai_active", {})
    assert event == NoRuleEvent(EVENT_ID, event_name)


def test_an_unknown_event_name_is_refused() -> None:
    with pytest.raises(ValueError, match=r"event name 'policy\.ran' is not one of"):
        parse_stored_event(EVENT_ID, "policy.ran", PROCESS_ID, "ai_active", {})
