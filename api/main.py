from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.infrastructure.config.settings import require_jwt_secret, settings
from api.infrastructure.db.pool import open_pool
from api.presentation.http.errors import install_error_handlers
from api.presentation.http.routes import cases, config, consultants, customers, health, products, session
from api.presentation.worker.loop import Worker, read_turn_for


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    require_jwt_secret(settings.jwt_secret)
    pool = open_pool(settings.database_url, settings.db_pool_min, settings.db_pool_max)
    app.state.pool = pool
    read_turn = read_turn_for(settings.llm_model)
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


app = FastAPI(title="Alba", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
install_error_handlers(app)
app.include_router(session.router)
app.include_router(session.consultant_router)
app.include_router(customers.router)
app.include_router(products.router)
app.include_router(cases.router)
app.include_router(consultants.router)
app.include_router(config.router)
app.include_router(health.router)
