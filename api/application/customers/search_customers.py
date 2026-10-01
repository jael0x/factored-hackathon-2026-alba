from dataclasses import dataclass
from typing import Protocol

from api.domain.customers.identity import CustomerHit
from api.domain.customers.search import SearchByText, parse_customer_search


class CustomerSearch(Protocol):
    def search(self, query: str) -> list[CustomerHit]: ...

    def pick_random_with_email(self) -> list[CustomerHit]: ...


@dataclass(frozen=True)
class RejectedSearch:
    pass


def search_customers(
    directory: CustomerSearch, q: str | None, random: bool | None
) -> list[CustomerHit] | RejectedSearch:
    parsed = parse_customer_search(q, random)
    if parsed is None:
        return RejectedSearch()
    if isinstance(parsed, SearchByText):
        return directory.search(parsed.query)
    return directory.pick_random_with_email()
