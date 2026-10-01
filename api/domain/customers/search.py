from dataclasses import dataclass


@dataclass(frozen=True)
class SearchByText:
    query: str


@dataclass(frozen=True)
class SearchAtRandom:
    pass


def parse_customer_search(q: str | None, random: bool | None) -> SearchByText | SearchAtRandom | None:
    if (q is None) == (random is None) or random is False:
        return None
    if q is not None:
        return SearchByText(query=q)
    return SearchAtRandom()
