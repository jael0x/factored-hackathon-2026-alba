from api.infrastructure.db.customers import escape_like


def test_escape_like_keeps_wildcards_literal() -> None:
    assert escape_like("50%_off\\") == "50\\%\\_off\\\\"
