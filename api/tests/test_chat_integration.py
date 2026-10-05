from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from api.application.cycle import moves
from api.contract_models import Locale, ProductKey, Role
from api.domain.policy.templates import certificate_for_policy, render_notice
from api.domain.session.tokens import SessionClaims, issue_token
from api.infrastructure.config.settings import settings
from api.infrastructure.llm.keywords import B0_MODEL
from api.main import app
from api.tests.cycle_harness import GOLD_ROWS, MARIANA
from api.tests.login_harness import ALICIA, JUAN, JULIANA, NO_EMAIL, seed_people

pytestmark = pytest.mark.integration

CHAT_TEST_DB = "alba_chat_test"
AS_OF = "2026-06-17"
CARD_ES = "Quiero una tarjeta de crédito"
NEEDS_INCOME_ES = render_notice("needs_income", "es", "credit_card")
REFER_NOTICE_ES = render_notice("refer_notice", "es", "credit_card")


def seed_profiles(url: str) -> None:
    with psycopg.connect(url) as conn:
        conn.execute(
            """
            INSERT INTO customers (customer_id, document_number, first_name, last_name, email, country, segment,
                                   customer_status)
            VALUES (%s, '0000009643', 'Mariana Mónica', 'Acosta Rojas', NULL, 'Argentina', 'Basic', 'Active')
            """,
            (MARIANA,),
        )
        conn.cursor().executemany(
            """
            INSERT INTO customer_credit_profile (
                customer_id, first_name, last_name, country, segment, customer_status, credit_score, income_local,
                income_currency, income_usd, max_days_past_due, has_active_card, has_active_personal_loan, as_of,
                batch_id
            )
            VALUES (%s, 'x', 'x', %s, 'Basic', 'Active', %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [(*row, AS_OF, uuid4()) for row in GOLD_ROWS],
        )


@pytest.fixture(scope="module")
def chat_database(migrated_database: Callable[[str], str]) -> str:
    url = migrated_database(CHAT_TEST_DB)
    seed_people(url)
    seed_profiles(url)
    return url


@pytest.fixture
def http(chat_database: str, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    with psycopg.connect(chat_database) as conn:
        conn.execute("TRUNCATE commands, messages, events, processes")
    monkeypatch.setattr(settings, "database_url", chat_database)
    monkeypatch.setattr(settings, "llm_model", B0_MODEL)
    monkeypatch.setattr(settings, "run_worker", True)
    with TestClient(app) as client:
        yield client


def bearer(sub: str, role: Role = "customer") -> dict[str, str]:
    token = issue_token(settings.jwt_secret, SessionClaims(sub=sub, role=role), datetime.now(UTC))
    return {"Authorization": f"Bearer {token}"}


def post(http: TestClient, body: dict[str, Any], sub: str) -> dict[str, Any]:
    response = http.post("/messages", json=body, headers=bearer(sub))
    assert response.status_code == 200, response.text
    case = response.json()
    assert isinstance(case, dict)
    return case


def start(
    http: TestClient,
    product: ProductKey = "credit_card",
    sub: str = JUAN.customer_id,
    locale: Locale = "es",
    text: str = CARD_ES,
    message_id: UUID | None = None,
) -> dict[str, Any]:
    body = {"text": text, "client_message_id": str(message_id or uuid4()), "locale": locale, "product": product}
    return post(http, body, sub)


def say(http: TestClient, case: dict[str, Any], text: str, sub: str, locale: Locale = "es") -> dict[str, Any]:
    body = {"text": text, "client_message_id": str(uuid4()), "locale": locale, "process_id": case["process_id"]}
    return post(http, body, sub)


def lines(case: dict[str, Any]) -> list[tuple[str, str]]:
    return [(message["author"], message["body"]) for message in case["messages"]]


def commands(url: str) -> list[tuple[str, str, int]]:
    with psycopg.connect(url) as conn:
        rows = conn.execute("SELECT command_name, status, attempt_count FROM commands ORDER BY seq").fetchall()
    return [(name, status, attempts) for name, status, attempts in rows]


def test_juan_starts_from_the_home_and_gets_his_certificate_without_a_model_call(
    http: TestClient, chat_database: str
) -> None:
    case = start(http)
    assert (case["state"], case["end_reason"], case["product"]) == ("ended", "prequalified", "credit_card")
    assert lines(case) == [("customer", CARD_ES), ("template", case["certificate"]["body"])]
    assert case["messages"][-1]["event_id"] == case["certificate"]["event_id"]
    assert commands(chat_database) == [
        ("process.start", "done", 1),
        ("policy.run", "done", 1),
        ("decision.render", "done", 1),
        ("process.end", "done", 1),
    ]


def test_the_certificate_shows_the_income_the_run_read(http: TestClient) -> None:
    certificate = start(http)["certificate"]
    assert certificate["outcome"] == "PREQUALIFIED"
    assert certificate["body"] == certificate_for_policy("PREQUALIFIED", "es", "credit_card")
    assert (certificate["locale"], certificate["product"], certificate["as_of"]) == ("es", "credit_card", AS_OF)
    assert (certificate["income_local"], certificate["income_currency"]) == (306753.45, "MXN")
    assert certificate["income_usd"] == pytest.approx(17988.33, abs=0.01)


def test_a_case_started_in_portuguese_decides_in_portuguese(http: TestClient) -> None:
    case = start(http, locale="pt", text="Quero um cartão de crédito")
    assert case["locale"] == "pt"
    assert case["certificate"]["body"] == certificate_for_policy("PREQUALIFIED", "pt", "credit_card")


def test_mariana_does_not_prequalify_and_is_not_told_the_rule(http: TestClient) -> None:
    case = start(http, sub=MARIANA)
    assert (case["state"], case["end_reason"]) == ("ended", "not_prequalified")
    body = case["certificate"]["body"]
    assert body == certificate_for_policy("NOT_PREQUALIFIED", "es", "credit_card")
    assert "R02" not in body and "515" not in body


def test_alicia_is_told_a_person_will_review_and_the_case_goes_to_one(http: TestClient) -> None:
    case = start(http, sub=ALICIA.customer_id)
    assert case["state"] == "human_active"
    assert case["certificate"] is None
    assert lines(case)[-1] == ("template", REFER_NOTICE_ES)


def test_juliana_is_asked_her_income_and_prequalifies_with_it(http: TestClient) -> None:
    asked = start(http, sub=JULIANA.customer_id)
    assert (asked["state"], lines(asked)[-1]) == ("ai_active", ("template", NEEDS_INCOME_ES))
    decided = say(http, asked, "gano 45,000 pesos al mes", JULIANA.customer_id)
    assert (decided["state"], decided["end_reason"]) == ("ended", "prequalified")
    certificate = decided["certificate"]
    assert (certificate["income_local"], certificate["income_currency"]) == (45000, "MXN")
    assert certificate["income_usd"] is None


def test_an_income_in_another_countrys_currency_is_asked_again(http: TestClient) -> None:
    asked = start(http, sub=JULIANA.customer_id)
    again = say(http, asked, "gano 3,200,000 COP al mes", JULIANA.customer_id)
    assert again["state"] == "ai_active"
    assert [line for line in lines(again) if line == ("template", NEEDS_INCOME_ES)] == [
        ("template", NEEDS_INCOME_ES),
        ("template", NEEDS_INCOME_ES),
    ]


def test_naming_the_other_product_switches_the_case_and_asks_consent_in_the_thread(http: TestClient) -> None:
    asked = start(http, sub=JULIANA.customer_id)
    switched = say(http, asked, "quiero un préstamo personal", JULIANA.customer_id)
    assert switched["product"] == "personal_loan"
    assert lines(switched)[-1] == ("template", render_notice("confirm_prequalify", "es", "personal_loan"))


def test_naming_a_product_that_has_its_own_open_case_points_to_it(http: TestClient) -> None:
    card = start(http, sub=JULIANA.customer_id)
    start(http, product="personal_loan", sub=JULIANA.customer_id, text="Quiero un préstamo personal")
    pointed = say(http, card, "quiero un préstamo personal", JULIANA.customer_id)
    assert pointed["product"] == "credit_card"
    assert lines(pointed)[-1] == ("template", render_notice("product_case_open", "es", "personal_loan"))


def test_a_request_for_a_person_inside_a_case_hands_it_off(http: TestClient) -> None:
    asked = start(http, sub=JULIANA.customer_id)
    case = say(http, asked, "quiero hablar con una persona", JULIANA.customer_id)
    assert case["state"] == "human_active"


def test_the_home_lists_each_case_newest_first(http: TestClient) -> None:
    card = start(http, sub=JULIANA.customer_id)
    loan = start(http, product="personal_loan", sub=JULIANA.customer_id, text="Quiero un préstamo personal")
    response = http.get("/cases", headers=bearer(JULIANA.customer_id))
    assert response.status_code == 200
    assert [(item["process_id"], item["product"], item["state"]) for item in response.json()["cases"]] == [
        (loan["process_id"], "personal_loan", "ai_active"),
        (card["process_id"], "credit_card", "ai_active"),
    ]
    assert http.get("/cases", headers=bearer(ALICIA.customer_id)).json() == {"cases": []}


def test_starting_a_product_that_has_an_open_case_is_refused(http: TestClient) -> None:
    start(http, sub=JULIANA.customer_id)
    body = {"text": CARD_ES, "client_message_id": str(uuid4()), "locale": "es", "product": "credit_card"}
    response = http.post("/messages", json=body, headers=bearer(JULIANA.customer_id))
    assert (response.status_code, response.json()) == (409, {"error": "case_already_open"})


def test_a_message_to_an_ended_case_is_refused(http: TestClient) -> None:
    ended = start(http)
    body = {"text": "gracias", "client_message_id": str(uuid4()), "locale": "es", "process_id": ended["process_id"]}
    response = http.post("/messages", json=body, headers=bearer(JUAN.customer_id))
    assert (response.status_code, response.json()) == (409, {"error": "case_ended"})


def test_the_same_start_sent_twice_returns_the_same_case(http: TestClient, chat_database: str) -> None:
    message_id = uuid4()
    first = start(http, message_id=message_id)
    again = start(http, message_id=message_id)
    assert again == first
    assert len(commands(chat_database)) == 4


def test_a_message_id_sent_again_for_another_message_is_refused(http: TestClient) -> None:
    message_id = uuid4()
    start(http, sub=JULIANA.customer_id, message_id=message_id)
    body = {"text": "otra cosa", "client_message_id": str(message_id), "locale": "es", "product": "personal_loan"}
    response = http.post("/messages", json=body, headers=bearer(JULIANA.customer_id))
    assert (response.status_code, response.json()) == (409, {"error": "message_id_reused"})


@pytest.mark.parametrize(
    "target",
    [{}, {"product": "credit_card", "process_id": "11111111-1111-4111-8111-111111111111"}],
    ids=["neither", "both"],
)
def test_a_message_names_either_a_product_or_a_case(http: TestClient, target: dict[str, str]) -> None:
    body = {"text": "hola", "client_message_id": str(uuid4()), "locale": "es", **target}
    response = http.post("/messages", json=body, headers=bearer(JUAN.customer_id))
    assert (response.status_code, response.json()) == (422, {"error": "invalid_body"})


def test_another_customers_case_is_not_found(http: TestClient) -> None:
    case = start(http)
    assert http.get(f"/case/{case['process_id']}", headers=bearer(ALICIA.customer_id)).status_code == 404
    body = {"text": "hola", "client_message_id": str(uuid4()), "locale": "es", "process_id": case["process_id"]}
    assert http.post("/messages", json=body, headers=bearer(ALICIA.customer_id)).status_code == 404


def test_an_unknown_case_is_not_found(http: TestClient) -> None:
    assert http.get(f"/case/{uuid4()}", headers=bearer(JUAN.customer_id)).status_code == 404


def test_the_case_reads_back_the_same(http: TestClient) -> None:
    sent = start(http)
    read = http.get(f"/case/{sent['process_id']}", headers=bearer(JUAN.customer_id))
    assert read.json() == sent


def test_a_consultant_cannot_use_the_customer_routes(http: TestClient) -> None:
    consultant = bearer("AGT-OJ9N4FGYV9", "consultant")
    body = {"text": "hola", "client_message_id": str(uuid4()), "locale": "es", "product": "credit_card"}
    assert http.post("/messages", json=body, headers=consultant).status_code == 403
    assert http.get("/cases", headers=consultant).status_code == 403


def test_a_typed_question_is_answered_by_the_classifier_llm_model_names(http: TestClient) -> None:
    asked = start(http, sub=JULIANA.customer_id)
    answered = say(http, asked, "¿qué productos de crédito ofrecen?", JULIANA.customer_id)
    assert [author for author, _ in lines(answered)] == ["customer", "template", "customer", "assistant"]
    assert answered["state"] == "ai_active"


def test_a_customer_without_a_credit_profile_goes_to_a_person(http: TestClient, chat_database: str) -> None:
    case = start(http, sub=NO_EMAIL.customer_id)
    assert case["state"] == "human_active"
    assert ("policy.run", "failed", 3) in commands(chat_database)


def test_a_case_that_cannot_open_fails_the_send_and_leaves_no_process(
    http: TestClient, chat_database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(*_: object) -> None:
        raise RuntimeError("the process table is unavailable")

    monkeypatch.setattr(moves, "start_process", refuse)
    body = {"text": CARD_ES, "client_message_id": str(uuid4()), "locale": "es", "product": "credit_card"}
    with pytest.raises(LookupError, match="opened no case"):
        http.post("/messages", json=body, headers=bearer(JUAN.customer_id))
    assert commands(chat_database) == [("process.start", "failed", 3), ("policy.run", "failed", 0)]


def test_mariana_asks_a_person_to_review_her_no_and_the_case_reopens_for_one(http: TestClient) -> None:
    decided = start(http, sub=MARIANA)
    response = http.post(f"/case/{decided['process_id']}/appeal", json={"locale": "es"}, headers=bearer(MARIANA))
    assert response.status_code == 200
    reopened = response.json()
    assert (reopened["state"], reopened["end_reason"]) == ("human_active", None)
    assert reopened["certificate"]["outcome"] == "NOT_PREQUALIFIED"
    assert lines(reopened) == [
        ("customer", CARD_ES),
        ("template", reopened["certificate"]["body"]),
        ("template", REFER_NOTICE_ES),
    ]
    assert reopened["messages"][1]["event_id"] == reopened["certificate"]["event_id"]
    again = http.post(f"/case/{decided['process_id']}/appeal", json={"locale": "es"}, headers=bearer(MARIANA))
    assert (again.status_code, again.json()) == (200, reopened)


def test_a_prequalified_result_cannot_be_appealed(http: TestClient) -> None:
    decided = start(http)
    response = http.post(
        f"/case/{decided['process_id']}/appeal", json={"locale": "es"}, headers=bearer(JUAN.customer_id)
    )
    assert (response.status_code, response.json()) == (409, {"error": "case_not_appealable"})


def test_an_open_case_cannot_be_appealed(http: TestClient) -> None:
    asked = start(http, sub=JULIANA.customer_id)
    response = http.post(
        f"/case/{asked['process_id']}/appeal", json={"locale": "es"}, headers=bearer(JULIANA.customer_id)
    )
    assert (response.status_code, response.json()) == (409, {"error": "case_not_appealable"})


def test_another_customers_case_cannot_be_appealed(http: TestClient) -> None:
    decided = start(http, sub=MARIANA)
    response = http.post(
        f"/case/{decided['process_id']}/appeal", json={"locale": "es"}, headers=bearer(JUAN.customer_id)
    )
    assert response.status_code == 404
