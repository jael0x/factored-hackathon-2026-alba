from dataclasses import dataclass

from api.domain.agents.identity import AgentIdentity

ACTIVE_STATUS = "Active"


@dataclass(frozen=True)
class AgentLoginKey:
    email: str
    employee_code: str


def login_key(email: str, employee_code: str) -> AgentLoginKey:
    return AgentLoginKey(email=email.strip().lower(), employee_code=employee_code.strip().upper())


def can_receive_code(agent: AgentIdentity) -> bool:
    return agent.agent_status == ACTIVE_STATUS
