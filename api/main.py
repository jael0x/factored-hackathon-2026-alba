from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.infrastructure.config.settings import require_jwt_secret, settings
from api.infrastructure.db.pool import open_pool
from api.presentation.http.errors import install_error_handlers
from api.presentation.http.routes import agents, config, customers, health, session


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    require_jwt_secret(settings.jwt_secret)
    pool = open_pool(settings.database_url, settings.db_pool_min, settings.db_pool_max)
    app.state.pool = pool
    try:
        yield
    finally:
        pool.close()


app = FastAPI(title="Alba", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
install_error_handlers(app)
app.include_router(session.router)
app.include_router(session.agent_router)
app.include_router(customers.router)
app.include_router(agents.router)
app.include_router(config.router)
app.include_router(health.router)
