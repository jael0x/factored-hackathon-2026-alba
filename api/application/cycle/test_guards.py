from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import date
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
    stored,
)
from api.application.cycle.generate import turn_request
from api.application.cycle.handlers import HANDLERS, require_handlers
from api.application.cycle.moves import end_case, hand_off_case
from api.application.cycle.notices import send_template
from api.application.cycle.policy_run import run_policy
from api.application.cycle.ports import EventRow, TurnRequest
from api.application.cycle.render import render_decision
from api.contract_models import MessageAuthor, ProductKey, ReasonCode, RuleId
from api.domain.policy.engine import CreditProfile
from api.domain.policy.templates import handoff_notice
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
from api.domain.process.stored_events import MessageReceived
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
    product: ProductKey | None = None

    def read(self, process_id: UUID) -> ProcessRow | None:
        return self.process

    def product_of(self, process_id: UUID) -> ProductKey | None:
        return self.product

    def store_turn_facts(self, *_args: object) -> None:
        raise AssertionError("not called")

    def open_products(self, *_args: object) -> frozenset[ProductKey]:
        raise AssertionError("not called")

    def find_open(self, *_args: object) -> ProcessRow | None:
        return self.process

    def read_for_message(self, customer_id: str, process_id: UUID) -> ProcessRow | None:
        raise AssertionError("not called")

    def insert_open(self, *_args: object) -> UUID | None:
        raise AssertionError("not called")

    def lock(self, process_id: UUID) -> ProcessRow | None:
        return self.process

    def set_state(self, *_args: object) -> None:
        raise AssertionError("not called")


@dataclass
class OneEvent:
    row: EventRow

    def read(self, event_id: UUID) -> EventRow:
        if event_id != self.row.event_id:
            raise LookupError(f"event {event_id} is not in this log")
        return self.row

    def earlier(self, *_args: object) -> list[EventRow]:
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
ANALYSIS = {
    "outcome": "PREQUALIFIED",
    "product": "credit_card",
    "locale": "es",
    "policy_version": "alba-credit-v1",
    "deciding_rule": "R05",
}


def test_a_trigger_of_the_wrong_kind_is_named() -> None:
    with pytest.raises(WrongTrigger, match="needs Decimal, got str"):
        expect("45000", Decimal)


def test_an_event_with_no_process_cannot_be_acted_on() -> None:
    with pytest.raises(LookupError, match=f"event {EVENT_ID} names no process"):
        process_id_of(trigger("conversation.message_received", MESSAGE, process_id=None))


def test_a_policy_run_follows_only_a_consented_turn_or_a_started_case() -> None:
    with pytest.raises(WrongTrigger, match="needs a shown turn or a started case, got AnalysisCompleted"):
        run_policy(
            cycle(Recorder()), trigger("analysis.completed", ANALYSIS), PolicyRunPayload("credit_card", None, None)
        )


def test_a_message_outside_a_command_never_reaches_the_model() -> None:
    message = MessageReceived(EVENT_ID, PROCESS_ID, "ai_active", "es", "hola", None)
    profile = CreditProfile("Active", 750, None, None, None, 0, False, False, date(2026, 6, 17))
    with pytest.raises(ValueError, match=f"message {EVENT_ID} reached the model outside a command"):
        turn_request(message, OPEN_CASE, profile, None)


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
    decided = trigger("prequalification.decided", {"outcome": "PREQUALIFIED", "decided_by": "policy", "locale": "es"})
    with pytest.raises(LookupError, match=f"policy certificate {EVENT_ID} names no analysis"):
        end_case(cycle(Recorder()), decided, EndPayload("prequalified"))


def test_a_notice_follows_only_a_turn_or_an_analysis() -> None:
    closed = trigger("conversation.consultant_closed", {"outcome": "PREQUALIFIED", "locale": "es"})
    with pytest.raises(WrongTrigger, match="needs a shown turn, an analysis, or a handoff, got ConsultantClosed"):
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


CAUSE_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
APPEAL = {"locale": "pt", "product": "credit_card"}
DECIDED = {"outcome": "PREQUALIFIED", "decided_by": "policy", "locale": "pt"}


def notice_after(reason: ReasonCode, cause_name: str, cause_payload: Mapping[str, object]) -> NewEvent:
    recorder = Recorder()
    cause = EventRow(CAUSE_ID, cause_name, JUAN, PROCESS_ID, "ai_active", None, 6, cause_payload)
    handoff_cycle = replace(cycle(recorder), case=OneCase(OPEN_CASE, "credit_card"), log=OneEvent(cause))
    taken = trigger("conversation.thread_taken", {"reason_code": reason}, caused_by=CAUSE_ID)
    send_template(handoff_cycle, taken, TemplatePayload("refer_notice"))
    [notice] = recorder.appended
    return notice


@pytest.mark.parametrize(
    ("reason", "cause_name", "cause_payload", "rule"),
    [
        (
            "policy_refer",
            "analysis.completed",
            {**ANALYSIS, "outcome": "REFER", "deciding_rule": "R04", "locale": "pt"},
            "R04",
        ),
        ("customer_requested_human", "conversation.appeal_requested", APPEAL, None),
        ("tool_failed", "conversation.message_received", {**MESSAGE, "locale": "pt"}, None),
        ("tool_failed", "prequalification.decided", DECIDED, None),
    ],
    ids=["policy", "appeal", "failed turn", "failed end"],
)
def test_a_handoff_notice_reads_its_locale_and_rule_from_the_event_that_caused_it(
    reason: ReasonCode, cause_name: str, cause_payload: Mapping[str, object], rule: RuleId | None
) -> None:
    body = handoff_notice("pt", "credit_card", reason, rule)
    notice = notice_after(reason, cause_name, cause_payload)
    assert (notice.event_name, notice.payload) == (
        "conversation.template_sent",
        {"locale": "pt", "template_id": "refer_notice", "body": body},
    )


def test_a_handoff_that_names_no_cause_is_refused() -> None:
    taken = trigger("conversation.thread_taken", {"reason_code": "out_of_scope"})
    with pytest.raises(LookupError, match=f"handoff {EVENT_ID} names no cause"):
        send_template(cycle(Recorder()), taken, TemplatePayload("refer_notice"))


def test_a_policy_handoff_not_caused_by_an_analysis_is_refused() -> None:
    with pytest.raises(WrongTrigger, match="needs AnalysisCompleted, got MessageReceived"):
        notice_after("policy_refer", "conversation.message_received", MESSAGE)


def test_a_handoff_caused_by_an_event_without_a_locale_is_refused() -> None:
    with pytest.raises(WrongTrigger, match="needs an event that carries a locale, got NoRuleEvent"):
        notice_after("tool_failed", "process.ended", {})
