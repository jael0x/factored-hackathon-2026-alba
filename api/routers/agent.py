from typing import Annotated

from fastapi import APIRouter, Depends

from api import agents, db
from api.auth import SessionClaims, require_agent
from api.contract_models import CurrentAgent
from api.errors import unauthorized

router = APIRouter()


@router.get("/agent/me", response_model=CurrentAgent)
def read_current_agent(session: Annotated[SessionClaims, Depends(require_agent)]) -> CurrentAgent:
    with db.connect() as conn:
        agent = agents.find_by_id(conn, session.sub)
    if agent is None:
        raise unauthorized()
    return agent
