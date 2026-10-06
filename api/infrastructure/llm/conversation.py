import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from uuid import UUID

import anthropic
from anthropic.types import Message

from api.application.cycle.ports import ReadTurn, TurnRequest
from api.contract_models import Intent, ProductKey
from api.domain.policy.engine import CREDIT_CARD, PERSONAL_LOAN
from api.domain.process.stored_events import PREQUALIFY_CARD_INTENT, PREQUALIFY_LOAN_INTENT
from api.domain.process.turns import ModelReading, ShownReading, WithheldReading, withheld_reason
from api.infrastructure.llm.prompt import PROMPT_VERSION, SYSTEM_PROMPT, turn_schema, user_message
from api.infrastructure.llm.schema import (
    ConversationTurn,
    InvalidConversationTurn,
    parse_conversation_turn,
    reading_of,
)

CLAUDE_SONNET_5_5 = "claude-sonnet-5-5"
# Classification needs little thinking; low effort keeps the reply fast (PLAN.md D27).
EFFORT = "low"
MAX_TOKENS = 4096
READS_PER_TURN = 2
TIMEOUT_SECONDS = 30.0
SDK_RETRIES = 2

PRODUCT_OF_INTENT: Mapping[Intent, ProductKey] = MappingProxyType(
    {PREQUALIFY_CARD_INTENT: CREDIT_CARD, PREQUALIFY_LOAN_INTENT: PERSONAL_LOAN}
)


@dataclass(frozen=True)
class LlmCall:
    process_id: UUID
    command_id: UUID
    model: str
    request: Mapping[str, object]
    raw_response: str | None
    parsed: Mapping[str, object] | None
    parse_ok: bool
    input_tokens: int
    cached_input_tokens: int
    cache_write_input_tokens: int
    output_tokens: int
    latency_ms: int


RecordCall = Callable[[LlmCall], None]
CreateMessage = Callable[..., Message]


class ModelOutputInvalid(Exception):
    pass


class ModelRefused(Exception):
    pass


class MissingApiKey(Exception):
    pass


# An organization-level key must name its workspace on every request; a workspace-scoped key needs none.
@dataclass(frozen=True)
class ClaudeAccess:
    api_key: str
    workspace_id: str | None


def workspace_header(access: ClaudeAccess) -> dict[str, str] | None:
    return None if access.workspace_id is None else {"anthropic-workspace-id": access.workspace_id}


# Two reads that do not parse fail the attempt, so the worker's three attempts end in tool_failed (PLAN.md D27).
class ClaudeTurnReader:
    def __init__(self, create: CreateMessage, model: str, record: RecordCall) -> None:
        self._create = create
        self.model = model
        self._record = record

    def __call__(self, request: TurnRequest) -> ModelReading:
        problems: list[str] = []
        for _ in range(READS_PER_TURN):
            turn = self._read_once(request, problems)
            if turn is not None:
                reading = reading_of(turn)
                reason = withheld_reason(reading.reply_text)
                return ShownReading(reading) if reason is None else WithheldReading(reading, reason)
        raise ModelOutputInvalid(f"{self.model} gave no valid turn in {READS_PER_TURN} reads: {'; '.join(problems)}")

    def _read_once(self, request: TurnRequest, problems: list[str]) -> ConversationTurn | None:
        started = time.monotonic()
        response = self._create(
            model=self.model,
            max_tokens=MAX_TOKENS,
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user_message(request)}],
            output_config={"effort": EFFORT, "format": {"type": "json_schema", "schema": turn_schema()}},
        )
        latency_ms = round((time.monotonic() - started) * 1000)
        raw = "".join(block.text for block in response.content if block.type == "text")
        turn, problem = parsed_turn(raw) if response.stop_reason != "refusal" else (None, "refused")
        self._record(call_of(request, self.model, response, raw, turn, latency_ms))
        if response.stop_reason == "refusal":
            raise ModelRefused(f"{self.model} declined the message ({stop_category(response)})")
        if problem is not None:
            problems.append(problem)
        return turn


def parsed_turn(raw: str) -> tuple[ConversationTurn | None, str | None]:
    try:
        return checked(parse_conversation_turn(raw)), None
    except InvalidConversationTurn as error:
        return None, str(error)


# A turn whose intent names one product while product names another, or none, is invalid output (IMPLEMENTATION.md M3).
def checked(turn: ConversationTurn) -> ConversationTurn:
    named = PRODUCT_OF_INTENT.get(turn.intent)
    if named is not None and turn.product != named:
        raise InvalidConversationTurn(f"intent {turn.intent} needs product {named}, got {turn.product}")
    return turn


def call_of(
    request: TurnRequest, model: str, response: Message, raw: str, turn: ConversationTurn | None, latency_ms: int
) -> LlmCall:
    usage = response.usage
    cache_read = usage.cache_read_input_tokens or 0
    cache_write = usage.cache_creation_input_tokens or 0
    return LlmCall(
        process_id=request.process_id,
        command_id=request.command_id,
        model=model,
        request={"prompt_version": PROMPT_VERSION, "effort": EFFORT, "message": user_message(request)},
        raw_response=raw,
        parsed=None if turn is None else turn.model_dump(),
        parse_ok=turn is not None,
        input_tokens=usage.input_tokens + cache_read + cache_write,
        cached_input_tokens=cache_read,
        cache_write_input_tokens=cache_write,
        output_tokens=usage.output_tokens,
        latency_ms=latency_ms,
    )


def stop_category(response: Message) -> str:
    details = response.stop_details
    return "no category" if details is None or details.category is None else str(details.category)


def claude_turn_reader(access: ClaudeAccess, model: str, record: RecordCall) -> ReadTurn:
    if not access.api_key:
        return missing_key
    client = anthropic.Anthropic(
        api_key=access.api_key,
        timeout=TIMEOUT_SECONDS,
        max_retries=SDK_RETRIES,
        default_headers=workspace_header(access),
    )
    return ClaudeTurnReader(client.messages.create, model, record)


def missing_key(_request: TurnRequest) -> ModelReading:
    raise MissingApiKey(
        "ANTHROPIC_API_KEY is not set in .env: conversation.generate cannot call Claude. "
        "Set it, or set LLM_MODEL=b0-keywords to read turns with the keyword baseline (PLAN.md D23)."
    )
