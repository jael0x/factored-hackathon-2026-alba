from datetime import UTC, datetime, timedelta
from uuid import uuid4

from api.domain.session import codes

SECRET = "unit-test-secret-0123456789abcdefghij"
NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)
SUBJECT = "CLI-9EDEKZ8OUNUR"


def issued(*, used_at: datetime | None = None, wrong_codes: int = 0) -> codes.IssuedCode:
    return codes.IssuedCode(
        id=uuid4(),
        code_hash=codes.hash_code(SECRET, SUBJECT, "481206"),
        expires_at=NOW + codes.CODE_TTL,
        wrong_codes=wrong_codes,
        used_at=used_at,
    )


def test_new_code_is_six_digits() -> None:
    generated = {codes.new_code() for _ in range(200)}
    assert all(len(code) == 6 and code.isdigit() for code in generated)
    assert len(generated) > 1


def test_hash_depends_on_subject_and_code() -> None:
    first = codes.hash_code(SECRET, SUBJECT, "481206")
    assert first == codes.hash_code(SECRET, SUBJECT, "481206")
    assert first != codes.hash_code(SECRET, "CLI-440CO5FZIY6A", "481206")
    assert first != codes.hash_code(SECRET, SUBJECT, "481207")
    assert "481206" not in first


def test_code_matches_only_the_issued_code() -> None:
    code = issued()
    assert codes.code_matches(SECRET, SUBJECT, code, "481206")
    assert not codes.code_matches(SECRET, SUBJECT, code, "481207")
    assert not codes.code_matches(SECRET, "CLI-440CO5FZIY6A", code, "481206")


def test_a_fresh_code_is_open() -> None:
    assert codes.code_is_open(issued(), NOW)


def test_a_used_code_is_closed() -> None:
    assert not codes.code_is_open(issued(used_at=NOW), NOW)


def test_a_code_is_closed_at_ten_minutes() -> None:
    assert codes.code_is_open(issued(), NOW + codes.CODE_TTL - timedelta(seconds=1))
    assert not codes.code_is_open(issued(), NOW + codes.CODE_TTL)


def test_four_wrong_codes_keep_it_open_and_five_close_it() -> None:
    assert codes.code_is_open(issued(wrong_codes=4), NOW)
    assert not codes.code_is_open(issued(wrong_codes=5), NOW)
