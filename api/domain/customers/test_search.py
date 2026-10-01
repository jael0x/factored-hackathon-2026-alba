from api.domain.customers.search import SearchAtRandom, SearchByText, parse_customer_search


def test_a_text_query_is_accepted() -> None:
    assert parse_customer_search("Juan", None) == SearchByText(query="Juan")


def test_a_random_pick_is_accepted() -> None:
    assert parse_customer_search(None, True) == SearchAtRandom()


def test_missing_both_criteria_is_rejected() -> None:
    assert parse_customer_search(None, None) is None


def test_both_criteria_are_rejected() -> None:
    assert parse_customer_search("Juan", True) is None


def test_random_false_is_rejected() -> None:
    assert parse_customer_search(None, False) is None
    assert parse_customer_search("Juan", False) is None
