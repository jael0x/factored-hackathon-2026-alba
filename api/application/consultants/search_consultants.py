from typing import Protocol

from api.domain.consultants.identity import ConsultantHit
from api.domain.search import RejectedSearch, SearchByText, parse_search


class ConsultantSearch(Protocol):
    def search_active(self, query: str) -> list[ConsultantHit]: ...

    def pick_random_active(self) -> list[ConsultantHit]: ...


def search_consultants(
    directory: ConsultantSearch, q: str | None, random: bool | None
) -> list[ConsultantHit] | RejectedSearch:
    parsed = parse_search(q, random)
    if parsed is None:
        return RejectedSearch()
    if isinstance(parsed, SearchByText):
        return directory.search_active(parsed.query)
    return directory.pick_random_active()
