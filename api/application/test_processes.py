from uuid import UUID

import pytest

from api.application.processes import OpenProcessVanished, start_process
from api.contract_models import EndReason, Locale, ProcessKey, ProcessState
from api.domain.process.lifecycle import ProcessRow
from api.domain.process.new_events import AppendResult, Cause, NewEvent

MESSAGE_ID = UUID("22222222-2222-4222-8222-222222222222")


class NoEvents:
    def append(self, event: NewEvent) -> AppendResult:
        raise AssertionError(f"nothing may be appended, got {event.event_name}")

    def has_key(self, idempotency_key: str) -> bool:
        return False

    def process_started_by(self, idempotency_key: str) -> UUID | None:
        return None


class OpenCaseEndedInBetween:
    def find_open(self, customer_id: str, process_key: ProcessKey) -> ProcessRow | None:
        return None

    def insert_open(self, customer_id: str, process_key: ProcessKey, locale: Locale) -> UUID | None:
        return None

    def lock(self, process_id: UUID) -> ProcessRow | None:
        raise AssertionError("start does not lock")

    def set_state(self, process_id: UUID, state: ProcessState, end_reason: EndReason | None) -> None:
        raise AssertionError("start does not move a process")


def test_an_open_case_that_blocked_the_insert_and_then_vanished_fails_loud() -> None:
    with pytest.raises(OpenProcessVanished, match="CLI-9EDEKZ8OUNUR"):
        start_process(NoEvents(), OpenCaseEndedInBetween(), "CLI-9EDEKZ8OUNUR", "es", Cause(MESSAGE_ID, None))
