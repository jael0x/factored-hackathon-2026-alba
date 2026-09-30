from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt

from api import auth
from api.customers import _like_escape
from api.mail import LOGIN_CODE_SUBJECT, login_code_message

SECRET = "unit-test-secret-0123456789abcdefghij"
NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)


def issued(**changes: object) -> auth.IssuedCode:
    base = {
        "id": uuid4(),
        "code_hash": auth.hash_code(SECRET, "CLI-9EDEKZ8OUNUR", "481206"),
        "expires_at": NOW + auth.CODE_TTL,
        "wrong_codes": 0,
        "used_at": None,
    }
    return auth.IssuedCode(**{**base, **changes})  # type: ignore[arg-type]


def test_new_code_is_six_digits() -> None:
    codes = {auth.new_code() for _ in range(200)}
    assert all(len(code) == 6 and code.isdigit() for code in codes)
    assert len(codes) > 1


def test_hash_depends_on_subject_and_code() -> None:
    first = auth.hash_code(SECRET, "CLI-9EDEKZ8OUNUR", "481206")
    assert first == auth.hash_code(SECRET, "CLI-9EDEKZ8OUNUR", "481206")
    assert first != auth.hash_code(SECRET, "CLI-440CO5FZIY6A", "481206")
    assert first != auth.hash_code(SECRET, "CLI-9EDEKZ8OUNUR", "481207")
    assert "481206" not in first


def test_code_matches_only_the_issued_code() -> None:
    code = issued()
    assert auth.code_matches(SECRET, "CLI-9EDEKZ8OUNUR", code, "481206")
    assert not auth.code_matches(SECRET, "CLI-9EDEKZ8OUNUR", code, "481207")
    assert not auth.code_matches(SECRET, "CLI-440CO5FZIY6A", code, "481206")


def test_a_fresh_code_is_open() -> None:
    assert auth.code_is_open(issued(), NOW)


def test_a_used_code_is_closed() -> None:
    assert not auth.code_is_open(issued(used_at=NOW), NOW)


def test_a_code_is_closed_at_ten_minutes() -> None:
    assert auth.code_is_open(issued(), NOW + auth.CODE_TTL - timedelta(seconds=1))
    assert not auth.code_is_open(issued(), NOW + auth.CODE_TTL)


def test_four_wrong_codes_keep_it_open_and_five_close_it() -> None:
    assert auth.code_is_open(issued(wrong_codes=4), NOW)
    assert not auth.code_is_open(issued(wrong_codes=5), NOW)


def test_token_round_trip() -> None:
    claims = auth.SessionClaims(sub="CLI-9EDEKZ8OUNUR", role="customer")
    token = auth.issue_token(SECRET, claims, datetime.now(UTC))
    assert auth.read_token(SECRET, token) == claims


def test_token_expires_after_fifteen_minutes() -> None:
    claims = auth.SessionClaims(sub="CLI-9EDEKZ8OUNUR", role="customer")
    token = auth.issue_token(SECRET, claims, datetime.now(UTC) - timedelta(minutes=16))
    assert auth.read_token(SECRET, token) is None


def test_token_signed_with_another_secret_is_rejected() -> None:
    claims = auth.SessionClaims(sub="CLI-9EDEKZ8OUNUR", role="customer")
    token = auth.issue_token("another-secret-0123456789abcdefghijkl", claims, datetime.now(UTC))
    assert auth.read_token(SECRET, token) is None


def test_token_with_an_unknown_role_is_rejected() -> None:
    now = datetime.now(UTC)
    token = jwt.encode({"sub": "CLI-9EDEKZ8OUNUR", "role": "admin", "exp": now + timedelta(minutes=5)}, SECRET, "HS256")
    assert auth.read_token(SECRET, token) is None


def test_login_code_message_names_code_and_validity() -> None:
    message = login_code_message("Alba <no-reply@alba.local>", "juan.romero@example.com", "481206")
    assert message["To"] == "juan.romero@example.com"
    assert message["Subject"] == LOGIN_CODE_SUBJECT
    body = message.get_content()
    assert "481206" in body
    assert "10 minutos" in body


def test_like_escape_keeps_wildcards_literal() -> None:
    assert _like_escape("50%_off\\") == "50\\%\\_off\\\\"
