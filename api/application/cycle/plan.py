from uuid import UUID

from api.application.cycle.context import stored
from api.application.cycle.ports import CommandQueue, EventLog
from api.application.processes import Events
from api.domain.process.new_events import AppendResult, NewEvent
from api.domain.process.rules import match_rules


class PlanningEvents:
    def __init__(self, events: Events, log: EventLog, queue: CommandQueue) -> None:
        self._events = events
        self._log = log
        self._queue = queue

    def append(self, event: NewEvent) -> AppendResult:
        result = self._events.append(event)
        for planned in match_rules(stored(self._log.read(result.event_id))):
            self._queue.enqueue(planned)
        return result

    def has_key(self, idempotency_key: str) -> bool:
        return self._events.has_key(idempotency_key)

    def process_started_by(self, idempotency_key: str) -> UUID | None:
        return self._events.process_started_by(idempotency_key)
