from api.application.customers.search_customers import RejectedSearch, search_customers
from api.domain.customers.identity import CustomerHit


class MemDirectory:
    def __init__(self) -> None:
        self.called = False

    def search(self, query: str) -> list[CustomerHit]:
        self.called = True
        return []

    def pick_random_with_email(self) -> list[CustomerHit]:
        self.called = True
        return []


def test_an_invalid_search_does_not_touch_the_directory() -> None:
    directory = MemDirectory()
    assert isinstance(search_customers(directory, None, None), RejectedSearch)
    assert isinstance(search_customers(directory, "Juan", True), RejectedSearch)
    assert directory.called is False


def test_a_text_search_uses_the_directory() -> None:
    directory = MemDirectory()
    assert search_customers(directory, "Juan", None) == []
    assert directory.called is True
