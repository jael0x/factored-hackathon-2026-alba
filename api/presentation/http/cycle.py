from uuid import UUID

import psycopg
from fastapi import Request

from api.application.cycle.plan import PlanningEvents
from api.infrastructure.db.commands import PostgresCommands
from api.infrastructure.db.events import PostgresEventLog, PostgresEvents
from api.presentation.http.errors import cycle_pending
from api.presentation.worker.loop import Worker, cycle_settled

CYCLE_WAIT_SECONDS = 30.0


def planning(conn: psycopg.Connection) -> PlanningEvents:
    return PlanningEvents(PostgresEvents(conn), PostgresEventLog(conn), PostgresCommands(conn))


def require_settled(request: Request, event_id: UUID) -> None:
    worker: Worker | None = request.app.state.worker
    if worker is None:
        settled = cycle_settled(request.app.state.pool, event_id)
    else:
        worker.wake()
        settled = worker.wait_for_cycle(event_id, CYCLE_WAIT_SECONDS)
    if not settled:
        raise cycle_pending()
