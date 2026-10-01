from api.application.session.ports import Agents
from api.domain.agents.identity import AgentIdentity


def read_current_agent(agents: Agents, agent_id: str) -> AgentIdentity | None:
    return agents.find_by_id(agent_id)
