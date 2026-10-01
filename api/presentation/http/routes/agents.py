from typing import Annotated

from fastapi import APIRouter, Depends, Query

from api.contract_models import AgentSearchHit, AgentSearchResults, CurrentAgent
from api.domain.agents.identity import AgentHit
from api.domain.search import RejectedSearch
from api.domain.session.tokens import SessionClaims
from api.presentation.http.dependencies import (
    ReadCurrentAgent,
    RunAgentSearch,
    get_demo_login,
    get_read_current_agent,
    get_run_agent_search,
    require_agent,
)
from api.presentation.http.errors import invalid_body, not_found, unauthorized

router = APIRouter()
search = APIRouter(prefix="/agents")


@router.get("/agent/me", response_model=CurrentAgent)
def read_me(
    session: Annotated[SessionClaims, Depends(require_agent)],
    read_agent: Annotated[ReadCurrentAgent, Depends(get_read_current_agent)],
) -> CurrentAgent:
    agent = read_agent(session.sub)
    if agent is None:
        raise unauthorized()
    return CurrentAgent(
        agent_id=agent.agent_id,
        employee_code=agent.employee_code,
        first_name=agent.first_name,
        last_name=agent.last_name,
        specialty=agent.specialty,
    )


@search.get("/search", response_model=AgentSearchResults)
def search_agents(
    run: Annotated[RunAgentSearch, Depends(get_run_agent_search)],
    demo_login: Annotated[bool, Depends(get_demo_login)],
    q: Annotated[str | None, Query(min_length=1)] = None,
    random: bool | None = None,
) -> AgentSearchResults:
    if not demo_login:
        raise not_found()
    found = run(q, random)
    if isinstance(found, RejectedSearch):
        raise invalid_body()
    return AgentSearchResults(agents=[_wire_hit(hit) for hit in found])


def _wire_hit(hit: AgentHit) -> AgentSearchHit:
    return AgentSearchHit(
        agent_id=hit.agent_id,
        employee_code=hit.employee_code,
        first_name=hit.first_name,
        last_name=hit.last_name,
        email=hit.email,
    )


router.include_router(search)
