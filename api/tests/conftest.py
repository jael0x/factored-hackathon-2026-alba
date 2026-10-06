import os
from collections.abc import Callable, Iterator

import psycopg
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-only-jwt-secret-0123456789abcdef")

from api.infrastructure.config.settings import settings
from api.infrastructure.llm.keywords import B0_MODEL
from api.infrastructure.mail.smtp import get_mailer
from api.main import app
from api.tests.chat_harness import CHAT_TEST_DB, reset, seed_profiles
from api.tests.login_harness import LOGIN_TEST_DB, FakeMailer, Harness, seed_people


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


@pytest.fixture(scope="module")
def chat_database(migrated_database: Callable[[str], str]) -> str:
    url = migrated_database(CHAT_TEST_DB)
    seed_people(url)
    seed_profiles(url)
    return url


@pytest.fixture
def http(chat_database: str, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    reset(chat_database)
    monkeypatch.setattr(settings, "database_url", chat_database)
    monkeypatch.setattr(settings, "llm_model", B0_MODEL)
    monkeypatch.setattr(settings, "run_worker", True)
    with TestClient(app) as client:
        yield client


# The API with no worker: a message is stored and its commands wait for run_until_idle.
@pytest.fixture
def idle_http(chat_database: str, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    reset(chat_database)
    monkeypatch.setattr(settings, "database_url", chat_database)
    monkeypatch.setattr(settings, "run_worker", False)
    with TestClient(app) as client:
        yield client
