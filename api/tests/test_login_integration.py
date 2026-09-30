from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import psycopg
import pytest
from fastapi.testclient import TestClient

from api import auth
from api.mail import get_mailer
from api.main import app
from api.settings import settings

pytestmark = pytest.mark.integration

TEST_DB = "alba_api_test"

JUAN = ("CLI-9EDEKZ8OUNUR", "71034840", "Juan Alberto", "Romero González", "juan.romero@example.com", "México")
ALICIA = ("CLI-440CO5FZIY6A", "1144095213", "Alicia Mariana", "Parra Álvarez", "alicia.parra@example.com", "Colombia")
JULIANA = ("CLI-MD60UR8PNJDI", "80526117", "Juliana", "Castro Gómez", "juliana.castro@example.com", "México")
NO_EMAIL = ("CLI-MOCK00000000", "52917380", "Rosa Elena", "Díaz Mora", None, "Colombia")
GONZALEZ = [
    (f"CLI-GONZ{index:08d}", f"4010{index:04d}", f"Cliente{index:02d}", "González Pérez", f"cliente{index}@example.com", "México")
    for index in range(22)
]
UNKNOWN_DOCUMENT = "00000000"


@dataclass
class FakeMailer:
    sent: list[tuple[str, str]] = field(default_factory=list)

    def send_login_code(self, to: str, code: str) -> None:
        self.sent.append((to, code))


@dataclass
class Harness:
    http: TestClient
    mail: FakeMailer

    def request_code(self, document_number: str) -> dict[str, object]:
        response = self.http.post("/session/code", json={"document_number": document_number})
        assert response.status_code == 200
        return response.json()

    def open_session(self, document_number: str, code: str) -> int:
        return self.http.post("/session", json={"document_number": document_number, "code": code}).status_code


@pytest.fixture(scope="module")
def database(migrated_database: Callable[[str], str]) -> str:
    url = migrated_database(TEST_DB)
    with psycopg.connect(url) as conn:
        conn.cursor().executemany(
            """
            INSERT INTO customers (customer_id, document_number, first_name, last_name, email, country, segment, customer_status)
            VALUES (%s, %s, %s, %s, %s, %s, 'Basic', 'Active')
            """,
            [JUAN, ALICIA, JULIANA, NO_EMAIL, *GONZALEZ],
        )
    return url


@pytest.fixture
def harness(database: str, monkeypatch: pytest.MonkeyPatch) -> Iterator[Harness]:
    with psycopg.connect(database) as conn:
        conn.execute("DELETE FROM login_codes")
    monkeypatch.setattr(settings, "database_url", database)
    monkeypatch.setattr(settings, "demo_login", True)
    mail = FakeMailer()
    app.dependency_overrides[get_mailer] = lambda: mail
    yield Harness(http=TestClient(app), mail=mail)
    app.dependency_overrides.clear()


def codes(*values: str) -> Iterator[str]:
    yield from values


def test_asking_for_a_code_emails_it_to_the_address_on_file(harness: Harness) -> None:
    assert harness.request_code(JUAN[1]) == {"expires_in_seconds": 600}
    assert len(harness.mail.sent) == 1
    to, code = harness.mail.sent[0]
    assert to == "juan.romero@example.com"
    assert len(code) == 6 and code.isdigit()


def test_the_stored_code_is_a_hash(harness: Harness) -> None:
    harness.request_code(JUAN[1])
    _, code = harness.mail.sent[0]
    with psycopg.connect(settings.database_url) as conn:
        stored = conn.execute("SELECT code_hash FROM login_codes").fetchall()
    assert len(stored) == 1
    assert code not in stored[0][0]


@pytest.mark.parametrize("document_number", [UNKNOWN_DOCUMENT, NO_EMAIL[1]])
def test_the_answer_does_not_reveal_whether_a_code_was_sent(harness: Harness, document_number: str) -> None:
    known = harness.request_code(JUAN[1])
    harness.mail.sent.clear()
    assert harness.request_code(document_number) == known
    assert harness.mail.sent == []


def test_a_code_with_its_document_number_opens_a_session(harness: Harness) -> None:
    harness.request_code(JUAN[1])
    _, code = harness.mail.sent[0]
    response = harness.http.post("/session", json={"document_number": JUAN[1], "code": code})
    assert response.status_code == 200
    body = response.json()
    assert body["sub"] == JUAN[0]
    assert body["role"] == "customer"
    me = harness.http.get("/me", headers={"Authorization": f"Bearer {body['token']}"})
    assert me.status_code == 200
    assert me.json() == {"customer_id": JUAN[0], "first_name": "Juan Alberto", "last_name": "Romero González"}


def test_a_code_older_than_ten_minutes_does_not_open_a_session(harness: Harness) -> None:
    harness.request_code(JUAN[1])
    _, code = harness.mail.sent[0]
    with psycopg.connect(settings.database_url) as conn:
        conn.execute(
            "UPDATE login_codes SET created_at = now() - interval '11 minutes', expires_at = now() - interval '1 minute'"
        )
    assert harness.open_session(JUAN[1], code) == 401


def test_a_code_entered_with_another_customers_document_does_not_open_a_session(harness: Harness) -> None:
    harness.request_code(JUAN[1])
    _, code = harness.mail.sent[0]
    assert harness.open_session(ALICIA[1], code) == 401


def test_a_document_number_without_a_code_does_not_open_a_session(harness: Harness) -> None:
    assert harness.open_session(JUAN[1], "123456") == 401
    missing_code = harness.http.post("/session", json={"document_number": JUAN[1]})
    assert missing_code.status_code == 422
    assert missing_code.json() == {"error": "invalid_body"}


def test_five_wrong_codes_spend_the_code(harness: Harness, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth, "new_code", lambda: "481206")
    harness.request_code(JUAN[1])
    assert [harness.open_session(JUAN[1], "000000") for _ in range(5)] == [401] * 5
    assert harness.open_session(JUAN[1], "481206") == 401


def test_four_wrong_codes_still_allow_the_right_one(harness: Harness, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth, "new_code", lambda: "481206")
    harness.request_code(JUAN[1])
    assert [harness.open_session(JUAN[1], "000000") for _ in range(4)] == [401] * 4
    assert harness.open_session(JUAN[1], "481206") == 200


def test_a_new_code_replaces_the_unused_one(harness: Harness, monkeypatch: pytest.MonkeyPatch) -> None:
    issued = codes("111111", "222222")
    monkeypatch.setattr(auth, "new_code", lambda: next(issued))
    harness.request_code(JUAN[1])
    harness.request_code(JUAN[1])
    assert harness.open_session(JUAN[1], "111111") == 401
    assert harness.open_session(JUAN[1], "222222") == 200


def test_a_used_code_does_not_open_a_second_session(harness: Harness) -> None:
    harness.request_code(JUAN[1])
    _, code = harness.mail.sent[0]
    assert harness.open_session(JUAN[1], code) == 200
    assert harness.open_session(JUAN[1], code) == 401


def test_an_expired_session_is_not_renewed(harness: Harness) -> None:
    claims = auth.SessionClaims(sub=JUAN[0], role="customer")
    token = auth.issue_token(settings.jwt_secret, claims, datetime.now(UTC) - timedelta(minutes=16))
    response = harness.http.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}


def test_me_without_a_token_is_401(harness: Harness) -> None:
    assert harness.http.get("/me").status_code == 401


def test_an_agent_token_cannot_read_a_customer_route(harness: Harness) -> None:
    token = auth.issue_token(settings.jwt_secret, auth.SessionClaims(sub="AGT-OJ9N4FGYV9", role="agent"), datetime.now(UTC))
    response = harness.http.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    assert response.json() == {"error": "forbidden"}


@pytest.mark.parametrize(("query", "customer_id"), [("Juliana Castro", JULIANA[0]), ("CLI-440CO5FZIY6A", ALICIA[0])])
def test_with_the_demo_login_on_a_visitor_finds_a_customer(harness: Harness, query: str, customer_id: str) -> None:
    response = harness.http.get("/customers/search", params={"q": query})
    assert response.status_code == 200
    assert customer_id in [hit["customer_id"] for hit in response.json()["customers"]]


def test_a_demo_search_lists_at_most_20_customers_in_name_order(harness: Harness) -> None:
    hits = harness.http.get("/customers/search", params={"q": "González"}).json()["customers"]
    assert len(hits) == 20
    keys = [(hit["last_name"], hit["first_name"], hit["customer_id"]) for hit in hits]
    assert keys == sorted(keys)


def test_a_demo_random_pick_is_a_customer_with_an_email(harness: Harness) -> None:
    picked = {harness.http.get("/customers/search", params={"random": "true"}).json()["customers"][0]["customer_id"] for _ in range(30)}
    assert NO_EMAIL[0] not in picked


def test_a_demo_search_needs_exactly_one_of_q_or_random(harness: Harness) -> None:
    assert harness.http.get("/customers/search").status_code == 422
    assert harness.http.get("/customers/search", params={"q": "Juan", "random": "true"}).status_code == 422


def test_with_the_demo_login_off_customers_cannot_be_searched(harness: Harness, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "demo_login", False)
    response = harness.http.get("/customers/search", params={"q": "Juliana Castro"})
    assert response.status_code == 404
    assert response.json() == {"error": "not_found"}
    assert harness.http.get("/config").json() == {"demo_login": False}
