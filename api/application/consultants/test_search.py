from api.application.consultants.search_consultants import search_consultants
from api.domain.consultants.identity import ConsultantHit
from api.domain.search import RejectedSearch

CESAR = ConsultantHit("AGT-OJ9N4FGYV9", "E75612", "César", "González Sánchez", "cesar.gonzalez@example.com")


class MemDirectory:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def search_active(self, query: str) -> list[ConsultantHit]:
        self.calls.append(f"search:{query}")
        return [CESAR]

    def pick_random_active(self) -> list[ConsultantHit]:
        self.calls.append("random")
        return [CESAR]


def test_an_invalid_consultant_search_does_not_touch_the_directory() -> None:
    directory = MemDirectory()
    assert isinstance(search_consultants(directory, None, None), RejectedSearch)
    assert isinstance(search_consultants(directory, "César", True), RejectedSearch)
    assert directory.calls == []


def test_a_text_search_asks_for_active_consultants() -> None:
    directory = MemDirectory()
    assert search_consultants(directory, "César", None) == [CESAR]
    assert directory.calls == ["search:César"]


def test_a_random_pick_asks_for_an_active_consultant() -> None:
    directory = MemDirectory()
    assert search_consultants(directory, None, True) == [CESAR]
    assert directory.calls == ["random"]
