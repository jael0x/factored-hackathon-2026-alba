from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from psycopg_pool import ConnectionPool

from api.application.cycle.ports import ReadTurn
from api.infrastructure.config.settings import claude_access, require_jwt_secret, settings
from api.infrastructure.db.llm_turns import PostgresLlmTurns
from api.infrastructure.db.pool import open_pool
from api.presentation.http.errors import install_error_handlers
from api.presentation.http.routes import (
    cases,
    config,
    consultant_cases,
    consultants,
    customers,
    health,
    products,
    session,
)
from api.presentation.worker.loop import Worker, read_turn_for

type ChooseReader = Callable[[ConnectionPool], ReadTurn]


# Claude's reader records every call in llm_turns, which needs the pool the process opens.
def reader_from_settings(pool: ConnectionPool) -> ReadTurn:
    return read_turn_for(settings.llm_model, claude_access(), PostgresLlmTurns(pool).record)


# The reader is chosen when the process starts, not when the app is built, so LLM_MODEL set before startup counts.
def create_app(choose_reader: ChooseReader = reader_from_settings) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        require_jwt_secret(settings.jwt_secret)
        pool = open_pool(settings.database_url, settings.db_pool_min, settings.db_pool_max)
        app.state.pool = pool
        read_turn = choose_reader(pool)
        worker = Worker(pool, read_turn) if settings.run_worker else None
        app.state.worker = worker
        if worker is not None:
            worker.start()
        try:
            yield
        finally:
            if worker is not None:
                worker.stop()
            pool.close()

    built = FastAPI(title="Alba", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    install_error_handlers(built)
    built.include_router(session.router)
    built.include_router(session.consultant_router)
    built.include_router(customers.router)
    built.include_router(products.router)
    built.include_router(cases.router)
    built.include_router(consultants.router)
    built.include_router(consultant_cases.router)
    built.include_router(config.router)
    built.include_router(health.router)
    return built


app = create_app()
