import psycopg
import pytest

from api.infrastructure.config.settings import settings
from api.tests.login_harness import (
    CESAR,
    INACTIVE,
    JUAN,
    ON_LEAVE,
    ON_VACATION,
    SHARED_CODE_DIEGO,
    SHARED_CODE_SOFIA,
    SHARED_EMAIL_ANDRES,
    SHARED_EMAIL_VALERIA,
    Harness,
    Login,
    consultant_login,
    customer_login,
    login_of,
)

pytestmark = pytest.mark.integration


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_an_active_consultant_gets_a_code_at_their_email(harness: Harness) -> None:
    assert harness.request_code(login_of(CESAR)) == {"expires_in_seconds": 600}
    assert len(harness.mail.sent) == 1
    to, code = harness.mail.sent[0]
    assert to == "cesar.gonzalez@example.com"
    assert len(code) == 6 and code.isdigit()


def test_spaces_and_letter_case_do_not_change_the_match(harness: Harness) -> None:
    typed = consultant_login("  Cesar.Gonzalez@EXAMPLE.com ", " e75612 ")
    harness.request_code(typed)
    assert [to for to, _ in harness.mail.sent] == ["cesar.gonzalez@example.com"]
    response = harness.http.post("/consultant/session", json={**typed.identity, "code": harness.last_code()})
    assert response.status_code == 200
    assert response.json()["sub"] == CESAR.consultant_id


@pytest.mark.parametrize(
    "login",
    [
        consultant_login("nadie@example.com", "E99999"),
        consultant_login(CESAR.email, SHARED_CODE_DIEGO.employee_code),
        login_of(ON_VACATION),
        login_of(ON_LEAVE),
        login_of(INACTIVE),
    ],
    ids=["unknown pair", "mixed pair", "Vacation", "Leave", "Inactive"],
)
def test_the_answer_does_not_reveal_whether_a_code_was_sent(harness: Harness, login: Login) -> None:
    known = harness.request_code(login_of(CESAR))
    harness.mail.sent.clear()
    assert harness.request_code(login) == known
    assert harness.mail.sent == []


def test_a_code_sent_while_active_does_not_open_a_session_after_the_consultant_leaves(
    harness: Harness, login_database: str
) -> None:
    harness.request_code(login_of(SHARED_EMAIL_ANDRES))
    code = harness.last_code()
    with psycopg.connect(login_database) as conn:
        conn.execute(
            "UPDATE service_agents SET agent_status = 'Leave' WHERE agent_id = %s", (SHARED_EMAIL_ANDRES.consultant_id,)
        )
    try:
        assert harness.open_session(login_of(SHARED_EMAIL_ANDRES), code) == 401
    finally:
        with psycopg.connect(login_database) as conn:
            conn.execute(
                "UPDATE service_agents SET agent_status = %s WHERE agent_id = %s",
                (SHARED_EMAIL_ANDRES.status, SHARED_EMAIL_ANDRES.consultant_id),
            )


def test_on_a_shared_employee_code_the_email_picks_the_consultant(harness: Harness) -> None:
    harness.request_code(login_of(SHARED_CODE_SOFIA))
    assert [to for to, _ in harness.mail.sent] == ["sofia.medina@example.com"]
    code = harness.last_code()
    assert harness.open_session(login_of(SHARED_CODE_DIEGO), code) == 401
    response = harness.http.post("/consultant/session", json={**login_of(SHARED_CODE_SOFIA).identity, "code": code})
    assert response.json()["sub"] == SHARED_CODE_SOFIA.consultant_id


def test_on_a_shared_email_the_employee_code_picks_the_consultant(harness: Harness) -> None:
    harness.request_code(login_of(SHARED_EMAIL_VALERIA))
    assert [to for to, _ in harness.mail.sent] == ["equipo.silva@example.com"]
    code = harness.last_code()
    assert harness.open_session(login_of(SHARED_EMAIL_ANDRES), code) == 401
    response = harness.http.post("/consultant/session", json={**login_of(SHARED_EMAIL_VALERIA).identity, "code": code})
    assert response.json()["sub"] == SHARED_EMAIL_VALERIA.consultant_id


def test_a_code_with_its_pair_opens_a_consultant_session(harness: Harness) -> None:
    harness.request_code(login_of(CESAR))
    response = harness.http.post("/consultant/session", json={**login_of(CESAR).identity, "code": harness.last_code()})
    assert response.status_code == 200
    body = response.json()
    assert body["sub"] == CESAR.consultant_id
    assert body["role"] == "consultant"
    me = harness.http.get("/consultant/me", headers=bearer(body["token"]))
    assert me.status_code == 200
    assert me.json() == {
        "consultant_id": CESAR.consultant_id,
        "employee_code": "E75612",
        "first_name": "César",
        "last_name": "González Sánchez",
        "specialty": "Créditos",
    }


def test_a_consultant_without_a_specialty_reads_it_as_null(harness: Harness) -> None:
    harness.request_code(login_of(SHARED_CODE_SOFIA))
    token = harness.token(login_of(SHARED_CODE_SOFIA), harness.last_code())
    assert harness.http.get("/consultant/me", headers=bearer(token)).json()["specialty"] is None


def test_a_customer_code_does_not_open_a_consultant_session(harness: Harness) -> None:
    harness.request_code(customer_login(JUAN.document_number))
    assert harness.open_session(login_of(CESAR), harness.last_code()) == 401


def test_a_consultant_code_does_not_open_a_customer_session(harness: Harness) -> None:
    harness.request_code(login_of(CESAR))
    assert harness.open_session(customer_login(JUAN.document_number), harness.last_code()) == 401


def test_a_customer_token_cannot_read_a_consultant_route(harness: Harness) -> None:
    harness.request_code(customer_login(JUAN.document_number))
    token = harness.token(customer_login(JUAN.document_number), harness.last_code())
    response = harness.http.get("/consultant/me", headers=bearer(token))
    assert response.status_code == 403
    assert response.json() == {"error": "forbidden"}


def test_consultant_me_without_a_token_is_401(harness: Harness) -> None:
    assert harness.http.get("/consultant/me").status_code == 401


def test_a_session_request_without_the_employee_code_is_invalid(harness: Harness) -> None:
    response = harness.http.post("/consultant/session", json={"email": CESAR.email, "code": "123456"})
    assert response.status_code == 422
    assert response.json() == {"error": "invalid_body"}


def test_with_the_demo_login_on_a_visitor_finds_an_active_consultant(harness: Harness) -> None:
    response = harness.http.get("/consultants/search", params={"q": "César González"})
    assert response.status_code == 200
    assert response.json() == {
        "consultants": [
            {
                "consultant_id": CESAR.consultant_id,
                "employee_code": "E75612",
                "first_name": "César",
                "last_name": "González Sánchez",
                "email": "cesar.gonzalez@example.com",
            }
        ]
    }


@pytest.mark.parametrize("query", ["Marta Ríos", "E20002", "AGT-TESTINA001"])
def test_a_demo_search_lists_only_active_consultants(harness: Harness, query: str) -> None:
    assert harness.http.get("/consultants/search", params={"q": query}).json() == {"consultants": []}


def test_a_demo_consultant_search_is_in_name_order(harness: Harness) -> None:
    hits = harness.http.get("/consultants/search", params={"q": "Medina"}).json()["consultants"]
    assert [hit["consultant_id"] for hit in hits] == [SHARED_CODE_SOFIA.consultant_id, SHARED_CODE_DIEGO.consultant_id]


def test_a_demo_random_pick_is_an_active_consultant(harness: Harness) -> None:
    inactive = {ON_VACATION.consultant_id, ON_LEAVE.consultant_id, INACTIVE.consultant_id}
    picked = {
        harness.http.get("/consultants/search", params={"random": "true"}).json()["consultants"][0]["consultant_id"]
        for _ in range(30)
    }
    assert picked.isdisjoint(inactive)


def test_a_demo_consultant_search_needs_exactly_one_of_q_or_random(harness: Harness) -> None:
    assert harness.http.get("/consultants/search").status_code == 422
    assert harness.http.get("/consultants/search", params={"q": "César", "random": "true"}).status_code == 422


def test_with_the_demo_login_off_consultants_cannot_be_searched(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "demo_login", False)
    response = harness.http.get("/consultants/search", params={"q": "César González"})
    assert response.status_code == 404
    assert response.json() == {"error": "not_found"}
