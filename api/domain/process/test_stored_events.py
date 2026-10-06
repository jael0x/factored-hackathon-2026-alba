from decimal import Decimal
from uuid import UUID

import pytest

from api.contract_models import EventName, Outcome, ProcessState, ReasonCode, TemplateId
from api.domain.process.stored_events import (
    AnalysisCompleted,
    ConsultantClosed,
    MessageReceived,
    NoRuleEvent,
    Payload,
    PrequalificationDecided,
    ProcessStarted,
    ShownTurn,
    TemplateSent,
    ThreadTaken,
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
        "locale": "es",
        "declared_income_amount": None,
        "declared_income_currency": None,
        "reply_text": "¿Tarjeta o préstamo?",
        "reply_ok": True,
        "reason_code": None,
        "product_asked_count": 0,
        "income_requested": False,
        "open_case_product": None,
        **overrides,
    }


def parse_turn(payload: Payload) -> object:
    return parse_stored_event(EVENT_ID, "conversation.turn_classified", PROCESS_ID, "ai_active", payload)


def parse_message(process_id: UUID | None, state: str, payload: Payload | None = None) -> object:
    message_payload = {"text": "hola", "locale": "es", "product": None} if payload is None else payload
    return parse_stored_event(EVENT_ID, "conversation.message_received", process_id, state, message_payload)


def test_a_first_message_has_no_process_and_the_birth_state() -> None:
    assert parse_message(None, "ai_active") == MessageReceived(EVENT_ID, None, "ai_active", "es", "hola", None)


def test_a_message_carries_the_locale_the_customer_chose() -> None:
    payload = {"text": "olá", "locale": "pt", "product": None}
    assert parse_message(None, "ai_active", payload) == MessageReceived(EVENT_ID, None, "ai_active", "pt", "olá", None)


def test_a_start_carries_the_product_confirmed_on_the_home() -> None:
    message = parse_message(None, "ai_active", {"text": "hola", "locale": "es", "product": "personal_loan"})
    assert message == MessageReceived(EVENT_ID, None, "ai_active", "es", "hola", "personal_loan")


@pytest.mark.parametrize(
    ("payload", "error", "kind"),
    [
        ({"locale": "es", "product": None}, "payload has no text", ValueError),
        ({"locale": "es", "text": 5, "product": None}, "text must be text", TypeError),
    ],
    ids=["missing", "number"],
)
def test_a_message_without_its_text_is_refused(payload: Payload, error: str, kind: type[Exception]) -> None:
    with pytest.raises(kind, match=error):
        parse_message(None, "ai_active", payload)


@pytest.mark.parametrize(
    ("payload", "error"),
    [({"text": "hi"}, "payload has no locale"), ({"text": "hi", "locale": "en"}, "'en' is not one of")],
    ids=["missing", "english"],
)
def test_a_message_without_a_supported_locale_is_refused(payload: Payload, error: str) -> None:
    with pytest.raises(ValueError, match=error):
        parse_message(None, "ai_active", payload)


@pytest.mark.parametrize("state", ["ai_active", "human_active"])
def test_a_message_in_an_open_case_carries_its_state(state: ProcessState) -> None:
    assert parse_message(PROCESS_ID, state) == MessageReceived(EVENT_ID, PROCESS_ID, state, "es", "hola", None)


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
        locale="es",
        intent="provide_income",
        product="credit_card",
        language="es",
        declared_income_amount=Decimal("45000.50"),
        declared_income_currency="MXN",
        product_asked_count=1,
        income_requested=True,
        reply_text="¿Tarjeta o préstamo?",
        open_case_product=None,
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
    assert parse_turn(payload) == WithheldTurn(EVENT_ID, "es", reason)


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
        ("language", "en"),
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
    payload = {
        "outcome": outcome,
        "product": "personal_loan",
        "locale": "pt",
        "policy_version": "alba-credit-v1",
        "deciding_rule": "R05",
    }
    event = parse_stored_event(EVENT_ID, "analysis.completed", PROCESS_ID, "ai_active", payload)
    assert event == AnalysisCompleted(EVENT_ID, outcome, "personal_loan", "pt", "alba-credit-v1", "R05")


@pytest.mark.parametrize(
    ("field", "value"),
    [("product", "mortgage"), ("locale", "en"), ("policy_version", "alba-credit-v2")],
)
def test_an_analysis_outside_the_contract_is_refused(field: str, value: str) -> None:
    payload = {
        "outcome": "REFER",
        "product": "credit_card",
        "locale": "es",
        "policy_version": "alba-credit-v1",
        "deciding_rule": "R05",
    }
    with pytest.raises(ValueError, match=f"{field} '{value}' is not one of"):
        parse_stored_event(EVENT_ID, "analysis.completed", PROCESS_ID, "ai_active", {**payload, field: value})


def test_a_decision_carries_its_outcome_and_who_decided() -> None:
    payload = {"outcome": "NOT_PREQUALIFIED", "decided_by": "consultant", "locale": "pt"}
    event = parse_stored_event(EVENT_ID, "prequalification.decided", PROCESS_ID, "human_active", payload)
    assert event == PrequalificationDecided(EVENT_ID, "NOT_PREQUALIFIED", "consultant", "pt")


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
    payload = {"outcome": "PREQUALIFIED", "consultant_id": "AGT-1", "locale": "pt"}
    event = parse_stored_event(EVENT_ID, "conversation.consultant_closed", PROCESS_ID, "human_active", payload)
    assert event == ConsultantClosed(EVENT_ID, "PREQUALIFIED", "pt")


@pytest.mark.parametrize(
    "event_name",
    [
        "process.state_changed",
        "process.ended",
    ],
)
def test_an_event_no_rule_reads_keeps_only_its_name(event_name: EventName) -> None:
    event = parse_stored_event(EVENT_ID, event_name, PROCESS_ID, "ai_active", {})
    assert event == NoRuleEvent(EVENT_ID, event_name)


def test_a_handoff_carries_its_reason() -> None:
    payload = {"reason_code": "policy_refer", "from_state": "ai_active", "to_state": "human_active"}
    event = parse_stored_event(EVENT_ID, "conversation.thread_taken", PROCESS_ID, "human_active", payload)
    assert event == ThreadTaken(EVENT_ID, "policy_refer")


def test_a_handoff_outside_the_reason_codes_is_refused() -> None:
    with pytest.raises(ValueError, match="reason_code 'tired' is not one of"):
        parse_stored_event(EVENT_ID, "conversation.thread_taken", PROCESS_ID, "human_active", {"reason_code": "tired"})


def test_a_started_case_carries_its_locale_and_product() -> None:
    payload = {
        "process_key": "credit_prequalification",
        "customer_id": "CLI-9",
        "locale": "pt",
        "product": "credit_card",
    }
    event = parse_stored_event(EVENT_ID, "process.started", PROCESS_ID, "ai_active", payload)
    assert event == ProcessStarted(EVENT_ID, "pt", "credit_card")


@pytest.mark.parametrize("template_id", ["confirm_prequalify", "which_product", "needs_income", "refer_notice"])
def test_a_sent_template_carries_its_template_id(template_id: TemplateId) -> None:
    payload = {"locale": "es", "template_id": template_id, "body": "…"}
    event = parse_stored_event(EVENT_ID, "conversation.template_sent", PROCESS_ID, "ai_active", payload)
    assert event == TemplateSent(EVENT_ID, template_id)


def test_a_sent_template_outside_the_set_is_refused() -> None:
    with pytest.raises(ValueError, match="template_id 'certificate' is not one of"):
        parse_stored_event(
            EVENT_ID, "conversation.template_sent", PROCESS_ID, "ai_active", {"template_id": "certificate"}
        )


def test_an_unknown_event_name_is_refused() -> None:
    with pytest.raises(ValueError, match=r"event name 'policy\.ran' is not one of"):
        parse_stored_event(EVENT_ID, "policy.ran", PROCESS_ID, "ai_active", {})
