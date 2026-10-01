from datetime import UTC, datetime, timedelta

import psycopg
import pytest

from api import auth
from api.settings import settings
from api.tests.login_harness import ALICIA, JULIANA, JUAN, NO_EMAIL, Harness, customer_login

pytestmark = pytest.mark.integration

UNKNOWN_DOCUMENT = "00000000"


def test_asking_for_a_code_emails_it_to_the_address_on_file(harness: Harness) -> None:
    assert harness.request_code(customer_login(JUAN.document_number)) == {"expires_in_seconds": 600}
    assert len(harness.mail.sent) == 1
    to, code = harness.mail.sent[0]
    assert to == "juan.romero@example.com"
    assert len(code) == 6 and code.isdigit()


def test_the_stored_code_is_a_hash(harness: Harness) -> None:
    harness.request_code(customer_login(JUAN.document_number))
    code = harness.last_code()
    with psycopg.connect(settings.database_url) as conn:
        stored = conn.execute("SELECT code_hash FROM login_codes").fetchall()
    assert len(stored) == 1
    assert code not in stored[0][0]


@pytest.mark.parametrize("document_number", [UNKNOWN_DOCUMENT, NO_EMAIL.document_number])
def test_the_answer_does_not_reveal_whether_a_code_was_sent(harness: Harness, document_number: str) -> None:
    known = harness.request_code(customer_login(JUAN.document_number))
    harness.mail.sent.clear()
    assert harness.request_code(customer_login(document_number)) == known
    assert harness.mail.sent == []


def test_a_code_with_its_document_number_opens_a_session(harness: Harness) -> None:
    harness.request_code(customer_login(JUAN.document_number))
    response = harness.http.post("/session", json={"document_number": JUAN.document_number, "code": harness.last_code()})
    assert response.status_code == 200
    body = response.json()
    assert body["sub"] == JUAN.customer_id
    assert body["role"] == "customer"
    me = harness.http.get("/me", headers={"Authorization": f"Bearer {body['token']}"})
    assert me.status_code == 200
    assert me.json() == {"customer_id": JUAN.customer_id, "first_name": "Juan Alberto", "last_name": "Romero González"}


def test_a_code_entered_with_another_customers_document_does_not_open_a_session(harness: Harness) -> None:
    harness.request_code(customer_login(JUAN.document_number))
    assert harness.open_session(customer_login(ALICIA.document_number), harness.last_code()) == 401


def test_a_document_number_without_a_code_does_not_open_a_session(harness: Harness) -> None:
    assert harness.open_session(customer_login(JUAN.document_number), "123456") == 401
    missing_code = harness.http.post("/session", json={"document_number": JUAN.document_number})
    assert missing_code.status_code == 422
    assert missing_code.json() == {"error": "invalid_body"}


def test_an_expired_session_is_not_renewed(harness: Harness) -> None:
    claims = auth.SessionClaims(sub=JUAN.customer_id, role="customer")
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


@pytest.mark.parametrize(("query", "customer_id"), [("Juliana Castro", JULIANA.customer_id), ("CLI-440CO5FZIY6A", ALICIA.customer_id)])
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
    assert NO_EMAIL.customer_id not in picked


def test_a_demo_search_needs_exactly_one_of_q_or_random(harness: Harness) -> None:
    assert harness.http.get("/customers/search").status_code == 422
    assert harness.http.get("/customers/search", params={"q": "Juan", "random": "true"}).status_code == 422


def test_with_the_demo_login_off_customers_cannot_be_searched(harness: Harness, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "demo_login", False)
    response = harness.http.get("/customers/search", params={"q": "Juliana Castro"})
    assert response.status_code == 404
    assert response.json() == {"error": "not_found"}
    assert harness.http.get("/config").json() == {"demo_login": False}
