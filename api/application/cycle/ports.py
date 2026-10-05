from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from api.contract_models import Locale, MessageAuthor, ProcessState, ProductKey
from api.domain.policy.engine import CreditProfile
from api.domain.process.commands import Command
from api.domain.process.lifecycle import ProcessRow
from api.domain.process.rules import PlannedCommand
from api.domain.process.turns import ModelReading


@dataclass(frozen=True)
class EventRow:
    event_id: UUID
    event_name: str
    customer_id: str
    process_id: UUID | None
    process_state: str
    caused_by_event_id: UUID | None
    seq: int
    payload: Mapping[str, object]


@dataclass(frozen=True)
class ClaimedCommand:
    command_id: UUID
    command: Command
    triggered_by_event_id: UUID
    attempt_count: int


@dataclass(frozen=True)
class TurnRequest:
    text: str
    locale: Locale
    process_state: ProcessState
    income_on_file: bool
    score_on_file: bool
    has_active_card: bool
    has_active_personal_loan: bool


ReadTurn = Callable[[TurnRequest], ModelReading]
Savepoint = Callable[[], AbstractContextManager[object]]


class CommandQueue(Protocol):
    def enqueue(self, planned: PlannedCommand) -> None: ...

    def claim_next(self) -> ClaimedCommand | None: ...

    def mark_done(self, command_id: UUID, attempt_count: int) -> None: ...

    def record_failure(self, command_id: UUID, attempt_count: int, error: str, final: bool) -> None: ...

    def fail_later_siblings(self, command_id: UUID) -> None: ...

    def cycle_settled(self, root_event_id: UUID) -> bool: ...


class EventLog(Protocol):
    def read(self, event_id: UUID) -> EventRow: ...

    def earlier(self, process_id: UUID, before_seq: int) -> list[EventRow]: ...


class Profiles(Protocol):
    def read(self, customer_id: str) -> CreditProfile | None: ...


class Thread(Protocol):
    def add_line(self, process_id: UUID, author: MessageAuthor, body: str, event_id: UUID) -> None: ...


class CaseFacts(Protocol):
    def read(self, process_id: UUID) -> ProcessRow | None: ...

    def product_of(self, process_id: UUID) -> ProductKey | None: ...

    def store_turn_facts(self, process_id: UUID, locale: Locale, product: ProductKey | None) -> None: ...

    def open_products(self, customer_id: str, except_process_id: UUID) -> frozenset[ProductKey]: ...
