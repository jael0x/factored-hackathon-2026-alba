from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from types import MappingProxyType
from typing import Any
from uuid import UUID

import pytest

from api.application.cycle.context import (
    Cycle,
    Handler,
    Trigger,
    WrongTrigger,
    expect,
    process_id_of,
    read_process,
    require_case,
    stored,
)
from api.application.cycle.handlers import HANDLERS, require_handlers
from api.application.cycle.moves import end_case, hand_off_case
from api.application.cycle.notices import send_template
from api.application.cycle.policy_run import run_policy
from api.application.cycle.ports import EventRow, TurnRequest
from api.application.cycle.render import render_decision
from api.contract_models import MessageAuthor, ProductKey
from api.domain.process.commands import (
    CommandName,
    EndPayload,
    PolicyRunPayload,
    RenderPayload,
    TemplatePayload,
    TransitionPayload,
)
from api.domain.process.lifecycle import ProcessRow
from api.domain.process.new_events import AlreadyAppended, AppendResult, Cause, NewEvent
from api.domain.process.turns import ModelReading

EVENT_ID = UUID("88888888-8888-4888-8888-888888888888")
PROCESS_ID = UUID("99999999-9999-4999-8999-999999999999")
COMMAND_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
JUAN = "CLI-9EDEKZ8OUNUR"
OPEN_CASE = ProcessRow(PROCESS_ID, JUAN, "ai_active")


@dataclass
class Recorder:
    appended: list[NewEvent] = field(default_factory=list)
    lines: list[tuple[UUID, MessageAuthor, str, UUID]] = field(default_factory=list)


@dataclass
class ReplayedEvents:
    recorder: Recorder

    def append(self, event: NewEvent) -> AppendResult:
        self.recorder.appended.append(event)
        return AlreadyAppended(EVENT_ID)

    def has_key(self, idempotency_key: str) -> bool:
        return True

    def process_started_by(self, idempotency_key: str) -> UUID | None:
        return None


@dataclass
class OneCase:
    process: ProcessRow | None

    def read(self, process_id: UUID) -> ProcessRow | None:
        return self.process

    def product_of(self, process_id: UUID) -> None:
        return None

    def store_turn_facts(self, *_args: object) -> None:
        raise AssertionError("not called")

    def open_products(self, *_args: object) -> frozenset[ProductKey]:
        raise AssertionError("not called")

    def find_open(self, *_args: object) -> ProcessRow | None:
        return self.process

    def read_for_message(self, process_id: UUID) -> ProcessRow | None:
        raise AssertionError("not called")

    def insert_open(self, *_args: object) -> UUID | None:
        raise AssertionError("not called")

    def lock(self, process_id: UUID) -> ProcessRow | None:
        return self.process

    def set_state(self, *_args: object) -> None:
        raise AssertionError("not called")


@dataclass
class Lines:
    recorder: Recorder

    def add_line(self, process_id: UUID, author: MessageAuthor, body: str, event_id: UUID) -> None:
        self.recorder.lines.append((process_id, author, body, event_id))


# Stands in for every port a guard path never reaches, so touching one fails the test instead of passing quietly.
class Unused:
    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"{name} is not used on this path")


def no_model(_request: TurnRequest) -> ModelReading:
    raise AssertionError("the model is not called on this path")


def cycle(recorder: Recorder, process: ProcessRow | None = OPEN_CASE) -> Cycle:
    case = OneCase(process)
    unused: Any = Unused()
    return Cycle(
        events=ReplayedEvents(recorder),
        processes=case,
        case=case,
        log=unused,
        queue=unused,
        profiles=unused,
        thread=Lines(recorder),
        read_turn=no_model,
    )


def trigger(
    event_name: str,
    payload: Mapping[str, object],
    process_id: UUID | None = PROCESS_ID,
    caused_by: UUID | None = None,
) -> Trigger:
    row = EventRow(EVENT_ID, event_name, JUAN, process_id, "ai_active", caused_by, 7, payload)
    return Trigger(row, stored(row), Cause(EVENT_ID, COMMAND_ID))


MESSAGE = {"text": "hola", "locale": "es", "product": None}
ANALYSIS = {"outcome": "PREQUALIFIED", "product": "credit_card", "locale": "es", "policy_version": "alba-credit-v1"}


def test_a_trigger_of_the_wrong_kind_is_named() -> None:
    with pytest.raises(WrongTrigger, match="needs Decimal, got str"):
        expect("45000", Decimal)


def test_an_event_with_no_process_cannot_be_acted_on() -> None:
    with pytest.raises(LookupError, match=f"event {EVENT_ID} names no process"):
        process_id_of(trigger("conversation.message_received", MESSAGE, process_id=None))


def test_a_message_with_no_process_and_no_product_belongs_to_no_case() -> None:
    message = trigger("conversation.message_received", MESSAGE, process_id=None)
    with pytest.raises(LookupError, match=f"event {EVENT_ID} belongs to no case"):
        require_case(cycle(Recorder()), message)


def test_a_policy_run_follows_only_a_consented_turn_or_a_start() -> None:
    with pytest.raises(WrongTrigger, match="needs a shown turn or a start, got AnalysisCompleted"):
        run_policy(
            cycle(Recorder()), trigger("analysis.completed", ANALYSIS), PolicyRunPayload("credit_card", None, None)
        )


def test_a_process_that_does_not_exist_is_named() -> None:
    with pytest.raises(LookupError, match=f"process {PROCESS_ID} does not exist"):
        read_process(cycle(Recorder(), process=None), PROCESS_ID)


def test_every_command_name_needs_a_handler() -> None:
    without_end: dict[CommandName, Handler] = {name: h for name, h in HANDLERS.items() if name != "process.end"}
    with pytest.raises(ValueError, match=r"every command needs one handler: \['process\.end'\]"):
        require_handlers(MappingProxyType(without_end))


def test_a_transition_only_moves_a_case_to_a_person() -> None:
    with pytest.raises(ValueError, match="only moves a case to human_active, not ended"):
        hand_off_case(
            cycle(Recorder()), trigger("analysis.completed", ANALYSIS), TransitionPayload("ended", "tool_failed")
        )


def test_a_policy_certificate_that_names_no_analysis_cannot_end_the_case() -> None:
    decided = trigger("prequalification.decided", {"outcome": "PREQUALIFIED", "decided_by": "policy"})
    with pytest.raises(LookupError, match=f"policy certificate {EVENT_ID} names no analysis"):
        end_case(cycle(Recorder()), decided, EndPayload("prequalified"))


def test_a_notice_follows_only_a_turn_or_an_analysis() -> None:
    closed = trigger("conversation.consultant_closed", {"outcome": "PREQUALIFIED", "locale": "es"})
    with pytest.raises(WrongTrigger, match="needs a shown turn, an analysis, or an appeal, got ConsultantClosed"):
        send_template(cycle(Recorder()), closed, TemplatePayload("refer_notice"))


def test_a_certificate_must_match_who_decided() -> None:
    with pytest.raises(ValueError, match="a consultant certificate cannot follow AnalysisCompleted"):
        render_decision(cycle(Recorder()), trigger("analysis.completed", ANALYSIS), RenderPayload("consultant"))


def test_a_replayed_notice_adds_no_second_thread_line() -> None:
    recorder = Recorder()
    send_template(cycle(recorder), trigger("analysis.completed", ANALYSIS), TemplatePayload("refer_notice"))
    assert [event.event_name for event in recorder.appended] == ["conversation.template_sent"]
    assert recorder.lines == []


def test_a_replayed_certificate_adds_no_second_thread_line() -> None:
    recorder = Recorder()
    render_decision(cycle(recorder), trigger("analysis.completed", ANALYSIS), RenderPayload("policy"))
    assert [event.event_name for event in recorder.appended] == ["prequalification.decided"]
    assert recorder.lines == []
