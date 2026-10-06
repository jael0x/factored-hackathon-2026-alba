from uuid import UUID

import pytest

from api.application.cycle.ports import TurnRequest
from api.domain.process.turns import ShownReading, WithheldReading
from api.infrastructure.llm.conversation import (
    ClaudeAccess,
    ClaudeTurnReader,
    LlmCall,
    MissingApiKey,
    ModelOutputInvalid,
    ModelRefused,
    claude_turn_reader,
    missing_key,
    workspace_header,
)
from api.infrastructure.llm.prompt import PROMPT_VERSION, SYSTEM_PROMPT, turn_schema
from api.infrastructure.llm.schema import reading_of
from api.tests.claude_harness import MODEL, ScriptedClaude, fixture_json, message
from api.tests.turn_harness import load_turn_fixture

PROCESS_ID = UUID("11111111-1111-4111-8111-111111111111")
COMMAND_ID = UUID("33333333-3333-4333-8333-333333333333")
CARD = "quiero una tarjeta de crédito"
REQUEST = TurnRequest(PROCESS_ID, COMMAND_ID, CARD, "es", "ai_active", True, True, False, False)
MESSAGE = (
    "Reply language: es\n"
    "Case state: ai_active\n"
    "On file: income yes, credit score yes, active credit card no, active personal loan no\n"
    f"<message>\n{CARD}\n</message>"
)


def reader(*replies: str, refused: bool = False) -> tuple[ClaudeTurnReader, ScriptedClaude, list[LlmCall]]:
    claude = ScriptedClaude([message(text, refused=refused, cache_read=1000) for text in replies])
    calls: list[LlmCall] = []
    return ClaudeTurnReader(claude, MODEL, calls.append), claude, calls


def test_a_valid_turn_is_shown_and_its_call_recorded() -> None:
    read, claude, calls = reader(fixture_json("es-quiero-una-tarjeta-de-credito"))
    assert read(REQUEST) == ShownReading(reading_of(load_turn_fixture("es-quiero-una-tarjeta-de-credito").turn))
    assert claude.requests == [
        {
            "model": MODEL,
            "max_tokens": 4096,
            "system": [{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": MESSAGE}],
            "output_config": {"effort": "low", "format": {"type": "json_schema", "schema": turn_schema()}},
        }
    ]
    [call] = calls
    assert (call.process_id, call.command_id, call.model, call.parse_ok) == (PROCESS_ID, COMMAND_ID, MODEL, True)
    assert call.request == {"prompt_version": PROMPT_VERSION, "effort": "low", "message": MESSAGE}
    assert (call.input_tokens, call.cached_input_tokens, call.cache_write_input_tokens, call.output_tokens) == (
        2200,
        1000,
        0,
        90,
    )
    assert call.parsed == load_turn_fixture("es-quiero-una-tarjeta-de-credito").turn.model_dump()


def test_a_reply_that_states_an_outcome_is_withheld() -> None:
    read, _, _ = reader(fixture_json("es-si-reply-states-outcome"))
    reading = reading_of(load_turn_fixture("es-si-reply-states-outcome").turn)
    assert read(REQUEST) == WithheldReading(reading, "reply_forbidden")


def test_an_invalid_turn_is_read_once_more() -> None:
    read, _, calls = reader('{"intent": "clarify"}', fixture_json("es-quiero-una-tarjeta-de-credito"))
    assert isinstance(read(REQUEST), ShownReading)
    assert [call.parse_ok for call in calls] == [False, True]
    assert (calls[0].parsed, calls[0].raw_response) == (None, '{"intent": "clarify"}')


def test_two_invalid_turns_fail_the_attempt_and_both_are_recorded() -> None:
    read, _, calls = reader("not json", '{"intent": "clarify"}')
    with pytest.raises(ModelOutputInvalid, match="gave no valid turn in 2 reads"):
        read(REQUEST)
    assert [call.parse_ok for call in calls] == [False, False]


def test_a_card_request_that_names_the_loan_is_invalid_output() -> None:
    card = load_turn_fixture("es-quiero-una-tarjeta-de-credito").turn.model_copy(update={"product": "personal_loan"})
    read, _, _ = reader(card.model_dump_json(), "{}")
    with pytest.raises(ModelOutputInvalid, match="intent prequalify_card needs product credit_card, got personal_loan"):
        read(REQUEST)


def test_a_refusal_fails_the_attempt_and_is_not_replaced() -> None:
    read, _, calls = reader("", refused=True)
    with pytest.raises(ModelRefused, match=f"{MODEL} declined the message \\(no category\\)"):
        read(REQUEST)
    assert [call.parse_ok for call in calls] == [False]


def test_without_a_key_the_reader_names_what_is_missing() -> None:
    assert claude_turn_reader(ClaudeAccess("", None), MODEL, lambda _call: None) is missing_key
    with pytest.raises(MissingApiKey, match=r"ANTHROPIC_API_KEY is not set in \.env"):
        missing_key(REQUEST)


def test_with_a_key_the_reader_is_claude() -> None:
    read = claude_turn_reader(ClaudeAccess("sk-ant-test", "wrkspc_test"), MODEL, lambda _call: None)
    assert isinstance(read, ClaudeTurnReader)
    assert read.model == MODEL


def test_an_organization_key_names_its_workspace_on_every_request() -> None:
    assert workspace_header(ClaudeAccess("sk-ant-test", "wrkspc_test")) == {"anthropic-workspace-id": "wrkspc_test"}
    assert workspace_header(ClaudeAccess("sk-ant-test", None)) is None
