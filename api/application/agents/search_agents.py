from typing import Protocol

from api.domain.agents.identity import AgentHit
from api.domain.search import RejectedSearch, SearchByText, parse_search


class AgentSearch(Protocol):
    def search_active(self, query: str) -> list[AgentHit]: ...

    def pick_random_active(self) -> list[AgentHit]: ...


def search_agents(directory: AgentSearch, q: str | None, random: bool | None) -> list[AgentHit] | RejectedSearch:
    parsed = parse_search(q, random)
    if parsed is None:
        return RejectedSearch()
    if isinstance(parsed, SearchByText):
        return directory.search_active(parsed.query)
    return directory.pick_random_active()
