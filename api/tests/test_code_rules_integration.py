from collections.abc import Iterator

import psycopg
import pytest

from api.domain.session import codes as login_codes
from api.infrastructure.config.settings import settings
from api.tests.login_harness import CESAR, JUAN, Harness, Login, customer_login, login_of

pytestmark = pytest.mark.integration

LOGINS = [customer_login(JUAN.document_number), login_of(CESAR)]


@pytest.fixture(params=LOGINS, ids=[login.role for login in LOGINS])
def login(request: pytest.FixtureRequest) -> Login:
    return request.param


def codes(*values: str) -> Iterator[str]:
    yield from values


def test_a_code_older_than_ten_minutes_does_not_open_a_session(harness: Harness, login: Login) -> None:
    harness.request_code(login)
    with psycopg.connect(settings.database_url) as conn:
        conn.execute(
            "UPDATE login_codes SET created_at = now() - interval '11 minutes', expires_at = now() - interval '1 minute'"
        )
    assert harness.open_session(login, harness.last_code()) == 401


def test_five_wrong_codes_spend_the_code(harness: Harness, login: Login, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(login_codes, "new_code", lambda: "481206")
    harness.request_code(login)
    assert [harness.open_session(login, "000000") for _ in range(5)] == [401] * 5
    assert harness.open_session(login, "481206") == 401


def test_four_wrong_codes_still_allow_the_right_one(harness: Harness, login: Login, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(login_codes, "new_code", lambda: "481206")
    harness.request_code(login)
    assert [harness.open_session(login, "000000") for _ in range(4)] == [401] * 4
    assert harness.open_session(login, "481206") == 200


def test_a_new_code_replaces_the_unused_one(harness: Harness, login: Login, monkeypatch: pytest.MonkeyPatch) -> None:
    issued = codes("111111", "222222")
    monkeypatch.setattr(login_codes, "new_code", lambda: next(issued))
    harness.request_code(login)
    harness.request_code(login)
    assert harness.open_session(login, "111111") == 401
    assert harness.open_session(login, "222222") == 200


def test_a_used_code_does_not_open_a_second_session(harness: Harness, login: Login) -> None:
    harness.request_code(login)
    code = harness.last_code()
    assert harness.open_session(login, code) == 200
    assert harness.open_session(login, code) == 401
