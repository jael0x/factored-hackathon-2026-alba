from decimal import Decimal

import pytest

from api.domain.process.commands import (
    GENERATE_COMMAND,
    SHOW_REPLY_COMMAND,
    Command,
    command_payload,
    end_process,
    hand_off,
    parse_command,
    render_decision,
    run_policy,
    send_template,
    start_process,
)

EVERY_COMMAND: list[tuple[Command, dict[str, object]]] = [
    (start_process("pt", "personal_loan"), {"locale": "pt", "product": "personal_loan"}),
    (GENERATE_COMMAND, {}),
    (SHOW_REPLY_COMMAND, {}),
    (send_template("which_product"), {"template_id": "which_product"}),
    (
        run_policy("credit_card", Decimal("45000.50"), "MXN"),
        {"product": "credit_card", "declared_income_amount": Decimal("45000.50"), "declared_income_currency": "MXN"},
    ),
    (
        run_policy("personal_loan", None, None),
        {"product": "personal_loan", "declared_income_amount": None, "declared_income_currency": None},
    ),
    (hand_off("tool_failed"), {"to_state": "human_active", "reason_code": "tool_failed"}),
    (render_decision("consultant"), {"decided_by": "consultant"}),
    (end_process("not_prequalified"), {"end_reason": "not_prequalified"}),
]


@pytest.mark.parametrize(("command", "payload"), EVERY_COMMAND)
def test_a_command_is_stored_as_its_payload_and_read_back_whole(command: Command, payload: dict[str, object]) -> None:
    assert command_payload(command.payload) == payload
    assert parse_command(command.command_name, payload) == command


def test_a_whole_amount_read_back_from_json_is_a_decimal() -> None:
    payload = {"product": "credit_card", "declared_income_amount": 45000, "declared_income_currency": None}
    assert parse_command("policy.run", payload) == run_policy("credit_card", Decimal(45000), None)


def test_a_float_amount_is_refused() -> None:
    payload = {"product": "credit_card", "declared_income_amount": 45000.5, "declared_income_currency": None}
    with pytest.raises(TypeError, match="must be read as Decimal, got float"):
        parse_command("policy.run", payload)


@pytest.mark.parametrize("name", ["conversation.generate", "conversation.show_reply"])
def test_a_command_with_no_payload_refuses_one(name: str) -> None:
    with pytest.raises(ValueError, match=r"takes no payload, got \['product'\]"):
        parse_command(name, {"product": "credit_card"})


def test_an_unknown_command_name_is_refused() -> None:
    with pytest.raises(ValueError, match=r"command name 'policy\.rerun' is not one of"):
        parse_command("policy.rerun", {})


@pytest.mark.parametrize(
    ("name", "payload", "error"),
    [
        ("process.start", {"locale": "en"}, "locale 'en' is not one of"),
        ("template.send", {"template_id": "certificate"}, "template_id 'certificate' is not one of"),
        ("process.transition", {"to_state": "started", "reason_code": "tool_failed"}, "to_state 'started'"),
        ("process.transition", {"to_state": "human_active", "reason_code": "bored"}, "reason_code 'bored'"),
        ("decision.render", {"decided_by": "model"}, "decided_by 'model' is not one of"),
        ("process.end", {"end_reason": "referred"}, "end_reason 'referred' is not one of"),
        ("process.end", {}, "payload has no end_reason"),
    ],
)
def test_a_payload_outside_the_contract_is_refused(name: str, payload: dict[str, object], error: str) -> None:
    with pytest.raises(ValueError, match=error):
        parse_command(name, payload)
