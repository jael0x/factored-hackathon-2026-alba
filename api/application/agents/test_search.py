from api.application.agents.search_agents import search_agents
from api.domain.agents.identity import AgentHit
from api.domain.search import RejectedSearch

CESAR = AgentHit("AGT-OJ9N4FGYV9", "E75612", "César", "González Sánchez", "cesar.gonzalez@example.com")


class MemDirectory:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def search_active(self, query: str) -> list[AgentHit]:
        self.calls.append(f"search:{query}")
        return [CESAR]

    def pick_random_active(self) -> list[AgentHit]:
        self.calls.append("random")
        return [CESAR]


def test_an_invalid_agent_search_does_not_touch_the_directory() -> None:
    directory = MemDirectory()
    assert isinstance(search_agents(directory, None, None), RejectedSearch)
    assert isinstance(search_agents(directory, "César", True), RejectedSearch)
    assert directory.calls == []


def test_a_text_search_asks_for_active_agents() -> None:
    directory = MemDirectory()
    assert search_agents(directory, "César", None) == [CESAR]
    assert directory.calls == ["search:César"]


def test_a_random_pick_asks_for_an_active_agent() -> None:
    directory = MemDirectory()
    assert search_agents(directory, None, True) == [CESAR]
    assert directory.calls == ["random"]
