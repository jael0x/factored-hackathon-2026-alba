import json
from collections.abc import Mapping
from dataclasses import dataclass, field

from anthropic.types import Message, TextBlock, Usage

from api.tests.turn_harness import TURN_FIXTURES, TurnFixtureName

MODEL = "claude-sonnet-5-5"


def message(text: str, *, refused: bool = False, cache_read: int = 0) -> Message:
    return Message(
        id="msg_test",
        type="message",
        role="assistant",
        model=MODEL,
        content=[TextBlock(type="text", text=text)],
        stop_reason="refusal" if refused else "end_turn",
        usage=Usage(input_tokens=1200, output_tokens=90, cache_read_input_tokens=cache_read),
    )


# The turn exactly as the fixture file writes it, so an amount stays a JSON number.
def fixture_json(name: TurnFixtureName) -> str:
    fixture = json.loads((TURN_FIXTURES / f"{name}.json").read_text())
    return json.dumps(fixture["turn"], ensure_ascii=False)


# Stands in for client.messages.create: answers with the scripted messages in order and keeps every request.
@dataclass
class ScriptedClaude:
    replies: list[Message]
    requests: list[Mapping[str, object]] = field(default_factory=list)

    def __call__(self, **params: object) -> Message:
        self.requests.append(params)
        return self.replies.pop(0)
