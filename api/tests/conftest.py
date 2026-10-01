import os
from collections.abc import Callable, Iterator

import psycopg
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-only-jwt-secret-0123456789abcdef")

from api.infrastructure.config.settings import settings  # noqa: E402
from api.infrastructure.mail.smtp import get_mailer  # noqa: E402
from api.main import app  # noqa: E402
from api.tests.login_harness import LOGIN_TEST_DB, FakeMailer, Harness, seed_people  # noqa: E402


@pytest.fixture(scope="module")
def login_database(migrated_database: Callable[[str], str]) -> str:
    url = migrated_database(LOGIN_TEST_DB)
    seed_people(url)
    return url


@pytest.fixture
def harness(login_database: str, monkeypatch: pytest.MonkeyPatch) -> Iterator[Harness]:
    with psycopg.connect(login_database) as conn:
        conn.execute("DELETE FROM login_codes")
    monkeypatch.setattr(settings, "database_url", login_database)
    monkeypatch.setattr(settings, "demo_login", True)
    mail = FakeMailer()
    app.dependency_overrides[get_mailer] = lambda: mail
    try:
        with TestClient(app) as client:
            yield Harness(http=client, mail=mail)
    finally:
        app.dependency_overrides.clear()
