from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from api.application.consultants.cases import (
    CaseAlreadyClosed,
    CaseNotClosable,
    ConsultantCaseNotFound,
    TraceRecord,
    close_consultant_case,
    read_handoff_packet,
)
from api.contract_models import ProcessState
from api.domain.policy.engine import CreditProfile, decide
from api.domain.process.case import CaseRow
from api.domain.process.events import transition_key
from api.domain.process.lifecycle import ProcessRow
from api.domain.process.new_events import (
    AlreadyAppended,
    Appended,
    AppendResult,
    Cause,
    IdempotencyConflict,
    NewEvent,
    analysis_completed,
    consultant_closed,
    thread_taken,
)
from api.domain.process.packet import HandoffSource, QueueItem, StoredEvent

PROCESS_ID = UUID("11111111-1111-4111-8111-111111111111")
CLOSE_ID = UUID("55555555-5555-4555-8555-555555555555")
ALICIA = "CLI-440CO5FZIY6A"
CESAR = "AGT-OJ9N4FGYV9"
CAUSE = Cause(event_id=UUID("44444444-4444-4444-8444-444444444444"), command_id=None)
CASE = ProcessRow(process_id=PROCESS_ID, customer_id=ALICIA, state="ai_active")


def analysis(score: int, income: Decimal | None) -> StoredEvent:
    profile = CreditProfile("Active", score, income, "COP", income, 0, False, False, date(2026, 6, 17))
    event = analysis_completed(CASE, decide(profile, "credit_card", None), "credit_card", "pt", CAUSE)
    return StoredEvent(UUID("22222222-2222-4222-8222-222222222222"), event.payload)


REFER = analysis(615, Decimal("4707334.28"))
NEEDS_INFO = analysis(714, None)
TAKEN = StoredEvent(
    UUID("33333333-3333-4333-8333-333333333333"),
    thread_taken(CASE, "policy_refer", transition_key(PROCESS_ID, "human_active", CAUSE.event_id), CAUSE).payload,
)


def source(state: ProcessState, result: StoredEvent | None = REFER) -> HandoffSource:
    return HandoffSource(PROCESS_ID, ALICIA, "Alicia Mariana", "Parra Álvarez", state, "pt", result, TAKEN)


@dataclass
class FakeCases:
    found: HandoffSource | None
    locked: list[UUID] = field(default_factory=list)

    def queue(self) -> list[QueueItem]:
        raise AssertionError("the close does not read the queue")

    def handoff(self, process_id: UUID) -> HandoffSource | None:
        return self.found

    def lock_handoff(self, process_id: UUID) -> HandoffSource | None:
        self.locked.append(process_id)
        return self.found

    def trace(self, process_id: UUID) -> list[TraceRecord] | None:
        raise AssertionError("the close does not read the trace")

    def case(self, process_id: UUID) -> CaseRow | None:
        raise AssertionError("the close does not read the case row")


@dataclass
class FakeEvents:
    answer: AppendResult | IdempotencyConflict = field(default_factory=lambda: Appended(CLOSE_ID))
    appended: list[NewEvent] = field(default_factory=list)

    def append(self, event: NewEvent) -> AppendResult:
        self.appended.append(event)
        if isinstance(self.answer, IdempotencyConflict):
            raise self.answer
        return self.answer

    def has_key(self, idempotency_key: str) -> bool:
        raise AssertionError("the close is keyed by its event")

    def process_started_by(self, idempotency_key: str) -> UUID | None:
        raise AssertionError("the close starts nothing")


def test_a_referred_case_is_closed_with_the_consultant_and_the_customers_locale() -> None:
    events, cases = FakeEvents(), FakeCases(source("human_active"))
    assert close_consultant_case(events, cases, CESAR, PROCESS_ID, "NOT_PREQUALIFIED") == CLOSE_ID
    assert events.appended == [
        consultant_closed(ProcessRow(PROCESS_ID, ALICIA, "human_active"), "NOT_PREQUALIFIED", CESAR, "pt")
    ]
    assert cases.locked == [PROCESS_ID]


@pytest.mark.parametrize(
    ("found", "refusal"),
    [
        (None, ConsultantCaseNotFound),
        (source("ai_active"), ConsultantCaseNotFound),
        (source("ended"), CaseAlreadyClosed),
        (source("human_active", NEEDS_INFO), CaseNotClosable),
        (source("human_active", None), CaseNotClosable),
    ],
)
def test_a_close_the_case_does_not_allow_appends_nothing(found: HandoffSource | None, refusal: type[Exception]) -> None:
    events = FakeEvents()
    with pytest.raises(refusal):
        close_consultant_case(events, FakeCases(found), CESAR, PROCESS_ID, "PREQUALIFIED")
    assert events.appended == []


@pytest.mark.parametrize("answer", [AlreadyAppended(CLOSE_ID), IdempotencyConflict("consultant_close:x")])
def test_a_second_close_of_the_case_is_already_closed(answer: AppendResult | IdempotencyConflict) -> None:
    with pytest.raises(CaseAlreadyClosed):
        close_consultant_case(FakeEvents(answer), FakeCases(source("human_active")), CESAR, PROCESS_ID, "PREQUALIFIED")


@pytest.mark.parametrize("state", ["ai_active", "ended"])
def test_only_a_case_with_a_person_has_a_packet(state: ProcessState) -> None:
    assert read_handoff_packet(FakeCases(source(state)), PROCESS_ID) is None


def test_an_unknown_case_has_no_packet() -> None:
    assert read_handoff_packet(FakeCases(None), PROCESS_ID) is None


def test_a_case_with_a_person_has_its_packet() -> None:
    packet = read_handoff_packet(FakeCases(source("human_active")), PROCESS_ID)
    assert packet is not None
    assert (packet.process_id, packet.reason_code, packet.closable) == (PROCESS_ID, "policy_refer", True)
