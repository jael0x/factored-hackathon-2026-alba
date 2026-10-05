from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar
from uuid import UUID

from api.application.cycle.ports import CaseFacts, CommandQueue, EventLog, EventRow, Profiles, ReadTurn, Thread
from api.application.processes import Events, Processes
from api.domain.policy.engine import CreditProfile
from api.domain.process.commands import CommandPayload
from api.domain.process.lifecycle import ProcessRow
from api.domain.process.new_events import Cause
from api.domain.process.stored_events import StoredEvent, parse_stored_event

Expected = TypeVar("Expected")


@dataclass(frozen=True)
class Cycle:
    events: Events
    processes: Processes
    case: CaseFacts
    log: EventLog
    queue: CommandQueue
    profiles: Profiles
    thread: Thread
    read_turn: ReadTurn


@dataclass(frozen=True)
class Trigger:
    row: EventRow
    event: StoredEvent
    cause: Cause


Handler = Callable[[Cycle, Trigger, CommandPayload], None]


class WrongTrigger(Exception):
    def __init__(self, needed: str, got: object) -> None:
        super().__init__(f"needs {needed}, got {type(got).__name__}")


def stored(row: EventRow) -> StoredEvent:
    return parse_stored_event(row.event_id, row.event_name, row.process_id, row.process_state, row.payload)


def expect(value: object, kind: type[Expected]) -> Expected:
    if not isinstance(value, kind):
        raise WrongTrigger(kind.__name__, value)
    return value


class MissingProfile(Exception):
    def __init__(self, customer_id: str) -> None:
        super().__init__(f"customer {customer_id} has no row in customer_credit_profile")


def require_profile(cycle: Cycle, customer_id: str) -> CreditProfile:
    profile = cycle.profiles.read(customer_id)
    if profile is None:
        raise MissingProfile(customer_id)
    return profile


def process_id_of(trigger: Trigger) -> UUID:
    process_id = trigger.row.process_id
    if process_id is None:
        raise LookupError(f"event {trigger.row.event_id} names no process")
    return process_id


def process_of(cycle: Cycle, trigger: Trigger) -> ProcessRow:
    return read_process(cycle, process_id_of(trigger))


def read_process(cycle: Cycle, process_id: UUID) -> ProcessRow:
    process = cycle.case.read(process_id)
    if process is None:
        raise LookupError(f"process {process_id} does not exist")
    return process
