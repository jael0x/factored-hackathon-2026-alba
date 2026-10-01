from dataclasses import dataclass


@dataclass(frozen=True)
class AgentIdentity:
    agent_id: str
    employee_code: str
    first_name: str
    last_name: str
    email: str
    agent_status: str
    specialty: str | None


@dataclass(frozen=True)
class AgentHit:
    agent_id: str
    employee_code: str
    first_name: str
    last_name: str
    email: str
