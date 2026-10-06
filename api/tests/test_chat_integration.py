from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.application.cycle import moves
from api.contract_models import CloseOutcome
from api.domain.policy.templates import certificate_for_close, certificate_for_policy, render_notice
from api.domain.process.stored_events import PRODUCT_INFO_INTENT
from api.infrastructure.llm.keywords import REPLIES, read_keyword_turn
from api.presentation.worker.loop import run_until_idle
from api.tests.chat_harness import (
    AS_OF,
    CARD_ES,
    CESAR,
    NEEDS_INCOME_ES,
    REFER_NOTICE_ES,
    appeal,
    bearer,
    certificate,
    close,
    commands,
    say,
    shape,
    start,
    start_body,
)
from api.tests.cycle_harness import MARIANA, cycle_pool
from api.tests.login_harness import ALICIA, JUAN, JULIANA, NO_EMAIL

pytestmark = pytest.mark.integration


def test_juan_starts_from_the_home_and_gets_his_certificate_without_a_model_call(
    http: TestClient, chat_database: str
) -> None:
    case = start(http)
    body = certificate_for_policy("PREQUALIFIED", "es", "credit_card")
    assert shape(case) == (
        "ended",
        "prequalified",
        "credit_card",
        "es",
        False,
        [("customer", CARD_ES), ("template", body)],
    )
    assert commands(chat_database) == [
        ("process.start", "done", 1),
        ("policy.run", "done", 1),
        ("decision.render", "done", 1),
        ("process.end", "done", 1),
    ]


def test_the_certificate_shows_the_income_its_analysis_read(http: TestClient) -> None:
    case = start(http)
    assert case["certificate"] == certificate(
        case,
        decided_by="policy",
        locale="es",
        outcome="PREQUALIFIED",
        body=certificate_for_policy("PREQUALIFIED", "es", "credit_card"),
        product="credit_card",
        income_local=306753.45,
        income_currency="MXN",
        income_usd=17988.33,
        as_of=AS_OF,
    )


def test_a_case_started_in_portuguese_decides_in_portuguese(http: TestClient) -> None:
    text = "Quero um cartão de crédito"
    case = start(http, locale="pt", text=text)
    body = certificate_for_policy("PREQUALIFIED", "pt", "credit_card")
    assert shape(case) == (
        "ended",
        "prequalified",
        "credit_card",
        "pt",
        False,
        [("customer", text), ("template", body)],
    )


def test_mariana_does_not_prequalify_is_not_told_the_rule_and_may_ask_a_person(http: TestClient) -> None:
    case = start(http, sub=MARIANA)
    body = certificate_for_policy("NOT_PREQUALIFIED", "es", "credit_card")
    assert shape(case) == (
        "ended",
        "not_prequalified",
        "credit_card",
        "es",
        True,
        [("customer", CARD_ES), ("template", body)],
    )
    assert "R02" not in body and "515" not in body


def test_alicia_is_told_a_person_will_review_and_the_case_goes_to_one(http: TestClient) -> None:
    case = start(http, sub=ALICIA.customer_id)
    expected = (
        "human_active",
        None,
        "credit_card",
        "es",
        False,
        [("customer", CARD_ES), ("template", REFER_NOTICE_ES)],
    )
    assert shape(case) == expected
    assert case["certificate"] is None


def test_juliana_is_asked_her_income_and_prequalifies_with_it(http: TestClient) -> None:
    asked = start(http, sub=JULIANA.customer_id)
    opening = [("customer", CARD_ES), ("template", NEEDS_INCOME_ES)]
    assert shape(asked) == ("ai_active", None, "credit_card", "es", False, opening)
    decided = say(http, asked, "gano 45,000 pesos al mes", JULIANA.customer_id)
    body = certificate_for_policy("PREQUALIFIED", "es", "credit_card")
    assert shape(decided) == (
        "ended",
        "prequalified",
        "credit_card",
        "es",
        False,
        [*opening, ("customer", "gano 45,000 pesos al mes"), ("template", body)],
    )
    assert decided["certificate"] == certificate(
        decided,
        decided_by="policy",
        locale="es",
        outcome="PREQUALIFIED",
        body=body,
        product="credit_card",
        income_local=45000,
        income_currency="MXN",
        income_usd=None,
        as_of=AS_OF,
    )


def test_an_income_in_another_countrys_currency_is_asked_again(http: TestClient) -> None:
    asked = start(http, sub=JULIANA.customer_id)
    again = say(http, asked, "gano 3,200,000 COP al mes", JULIANA.customer_id)
    assert shape(again) == (
        "ai_active",
        None,
        "credit_card",
        "es",
        False,
        [
            ("customer", CARD_ES),
            ("template", NEEDS_INCOME_ES),
            ("customer", "gano 3,200,000 COP al mes"),
            ("template", NEEDS_INCOME_ES),
        ],
    )


def test_naming_the_other_product_switches_the_case_and_asks_consent_in_the_thread(http: TestClient) -> None:
    asked = start(http, sub=JULIANA.customer_id)
    switched = say(http, asked, "quiero un préstamo personal", JULIANA.customer_id)
    assert shape(switched) == (
        "ai_active",
        None,
        "personal_loan",
        "es",
        False,
        [
            ("customer", CARD_ES),
            ("template", NEEDS_INCOME_ES),
            ("customer", "quiero un préstamo personal"),
            ("template", render_notice("confirm_prequalify", "es", "personal_loan")),
        ],
    )


def test_naming_a_product_that_has_its_own_open_case_points_to_it(http: TestClient) -> None:
    card = start(http, sub=JULIANA.customer_id)
    start(http, product="personal_loan", sub=JULIANA.customer_id, text="Quiero un préstamo personal")
    pointed = say(http, card, "quiero un préstamo personal", JULIANA.customer_id)
    assert shape(pointed) == (
        "ai_active",
        None,
        "credit_card",
        "es",
        False,
        [
            ("customer", CARD_ES),
            ("template", NEEDS_INCOME_ES),
            ("customer", "quiero un préstamo personal"),
            ("template", render_notice("product_case_open", "es", "personal_loan")),
        ],
    )


def test_a_request_for_a_person_inside_a_case_hands_it_off(http: TestClient) -> None:
    asked = start(http, sub=JULIANA.customer_id)
    case = say(http, asked, "quiero hablar con una persona", JULIANA.customer_id)
    assert shape(case) == (
        "human_active",
        None,
        "credit_card",
        "es",
        False,
        [("customer", CARD_ES), ("template", NEEDS_INCOME_ES), ("customer", "quiero hablar con una persona")],
    )


def test_the_home_lists_each_case_newest_first(http: TestClient) -> None:
    card = start(http, sub=JULIANA.customer_id)
    loan = start(http, product="personal_loan", sub=JULIANA.customer_id, text="Quiero un préstamo personal")
    response = http.get("/cases", headers=bearer(JULIANA.customer_id))
    assert response.status_code == 200
    assert response.json() == {
        "cases": [
            {
                "process_id": loan["process_id"],
                "product": "personal_loan",
                "state": "ai_active",
                "end_reason": None,
                "locale": "es",
            },
            {
                "process_id": card["process_id"],
                "product": "credit_card",
                "state": "ai_active",
                "end_reason": None,
                "locale": "es",
            },
        ]
    }
    assert http.get("/cases", headers=bearer(ALICIA.customer_id)).json() == {"cases": []}


def test_starting_a_product_that_has_an_open_case_is_refused(http: TestClient) -> None:
    start(http, sub=JULIANA.customer_id)
    response = http.post(
        "/messages", json=start_body("credit_card", "es", CARD_ES, None), headers=bearer(JULIANA.customer_id)
    )
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
    body = start_body("personal_loan", "es", "otra cosa", message_id)
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
    read = http.get(f"/case/{case['process_id']}", headers=bearer(ALICIA.customer_id))
    assert (read.status_code, read.json()) == (404, {"error": "not_found"})
    body = {"text": "hola", "client_message_id": str(uuid4()), "locale": "es", "process_id": case["process_id"]}
    sent = http.post("/messages", json=body, headers=bearer(ALICIA.customer_id))
    assert (sent.status_code, sent.json()) == (404, {"error": "not_found"})


def test_an_unknown_case_is_not_found(http: TestClient) -> None:
    read = http.get(f"/case/{uuid4()}", headers=bearer(JUAN.customer_id))
    assert (read.status_code, read.json()) == (404, {"error": "not_found"})


def test_the_case_reads_back_the_same(http: TestClient) -> None:
    sent = start(http)
    read = http.get(f"/case/{sent['process_id']}", headers=bearer(JUAN.customer_id))
    assert read.json() == sent


def test_a_consultant_cannot_use_the_customer_routes(http: TestClient) -> None:
    case = start(http, sub=MARIANA)
    consultant = bearer(CESAR, "consultant")
    forbidden = (403, {"error": "forbidden"})
    sent = http.post("/messages", json=start_body("credit_card", "es", "hola", None), headers=consultant)
    listed = http.get("/cases", headers=consultant)
    read = http.get(f"/case/{case['process_id']}", headers=consultant)
    appealed = http.post(f"/case/{case['process_id']}/appeal", json={"locale": "es"}, headers=consultant)
    assert [(r.status_code, r.json()) for r in (sent, listed, read, appealed)] == [forbidden] * 4


def test_a_typed_question_is_answered_by_the_classifier_llm_model_names(http: TestClient) -> None:
    asked = start(http, sub=JULIANA.customer_id)
    answered = say(http, asked, "¿qué productos de crédito ofrecen?", JULIANA.customer_id)
    assert shape(answered) == (
        "ai_active",
        None,
        "credit_card",
        "es",
        False,
        [
            ("customer", CARD_ES),
            ("template", NEEDS_INCOME_ES),
            ("customer", "¿qué productos de crédito ofrecen?"),
            ("assistant", REPLIES["es"][PRODUCT_INFO_INTENT]),
        ],
    )


def test_a_customer_without_a_credit_profile_goes_to_a_person(http: TestClient, chat_database: str) -> None:
    case = start(http, sub=NO_EMAIL.customer_id)
    assert shape(case) == ("human_active", None, "credit_card", "es", False, [("customer", CARD_ES)])
    assert commands(chat_database) == [("process.start", "done", 1), ("policy.run", "failed", 3)]


def test_a_case_that_cannot_open_fails_the_send_and_leaves_no_process(
    http: TestClient, chat_database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(*_: object) -> None:
        raise RuntimeError("the process table is unavailable")

    monkeypatch.setattr(moves, "start_process", refuse)
    with pytest.raises(LookupError, match="opened no case"):
        http.post("/messages", json=start_body("credit_card", "es", CARD_ES, None), headers=bearer(JUAN.customer_id))
    assert commands(chat_database) == [("process.start", "failed", 3)]


def test_without_a_worker_the_send_is_stored_and_answers_cycle_pending(
    idle_http: TestClient, chat_database: str
) -> None:
    response = idle_http.post(
        "/messages", json=start_body("credit_card", "es", CARD_ES, None), headers=bearer(JUAN.customer_id)
    )
    assert (response.status_code, response.json()) == (503, {"error": "cycle_pending"})
    assert commands(chat_database) == [("process.start", "pending", 0)]


def test_a_second_start_for_a_product_that_lost_to_the_first_is_refused(
    idle_http: TestClient, chat_database: str
) -> None:
    first, second = uuid4(), uuid4()
    for message_id in (first, second):
        body = start_body("credit_card", "es", CARD_ES, message_id)
        assert idle_http.post("/messages", json=body, headers=bearer(JUAN.customer_id)).status_code == 503
    with cycle_pool(chat_database) as pool:
        run_until_idle(pool, read_keyword_turn)
    won = idle_http.post(
        "/messages", json=start_body("credit_card", "es", CARD_ES, first), headers=bearer(JUAN.customer_id)
    )
    lost = idle_http.post(
        "/messages", json=start_body("credit_card", "es", CARD_ES, second), headers=bearer(JUAN.customer_id)
    )
    assert (won.status_code, won.json()["end_reason"]) == (200, "prequalified")
    assert (lost.status_code, lost.json()) == (409, {"error": "case_already_open"})
    assert [name for name, _, _ in commands(chat_database)].count("policy.run") == 1


def test_mariana_asks_a_person_to_review_her_no_and_the_case_reopens_for_one(http: TestClient) -> None:
    decided = start(http, sub=MARIANA)
    response = appeal(http, decided, MARIANA)
    assert response.status_code == 200
    reopened = response.json()
    body = certificate_for_policy("NOT_PREQUALIFIED", "es", "credit_card")
    assert shape(reopened) == (
        "human_active",
        None,
        "credit_card",
        "es",
        False,
        [("customer", CARD_ES), ("template", body), ("template", REFER_NOTICE_ES)],
    )
    assert reopened["messages"][1]["event_id"] == reopened["certificate"]["event_id"]
    again = appeal(http, decided, MARIANA)
    assert (again.status_code, again.json()) == (200, reopened)


def test_a_no_cannot_reopen_while_another_case_of_its_product_is_open(http: TestClient) -> None:
    first = start(http, sub=MARIANA)
    second = start(http, sub=MARIANA)
    assert appeal(http, second, MARIANA).status_code == 200
    read = http.get(f"/case/{first['process_id']}", headers=bearer(MARIANA)).json()
    assert (read["state"], read["appealable"]) == ("ended", False)
    response = appeal(http, first, MARIANA)
    assert (response.status_code, response.json()) == (409, {"error": "case_already_open"})


@pytest.mark.parametrize("outcome", ["PREQUALIFIED", "NOT_PREQUALIFIED"])
def test_a_consultant_certificate_shows_no_income_and_cannot_be_appealed(
    http: TestClient, chat_database: str, outcome: CloseOutcome
) -> None:
    referred = start(http, sub=ALICIA.customer_id)
    assert close(http, referred, outcome).status_code == 200
    closed = http.get(f"/case/{referred['process_id']}", headers=bearer(ALICIA.customer_id)).json()
    assert closed["certificate"] == certificate(
        closed,
        decided_by="consultant",
        locale="es",
        outcome=outcome,
        body=certificate_for_close(outcome, "es", "credit_card"),
        product="credit_card",
        income_local=None,
        income_currency=None,
        income_usd=None,
        as_of=None,
    )
    assert closed["appealable"] is False
    response = appeal(http, closed, ALICIA.customer_id)
    assert (response.status_code, response.json()) == (409, {"error": "case_not_appealable"})


def test_a_prequalified_result_cannot_be_appealed(http: TestClient) -> None:
    response = appeal(http, start(http), JUAN.customer_id)
    assert (response.status_code, response.json()) == (409, {"error": "case_not_appealable"})


def test_an_open_case_cannot_be_appealed(http: TestClient) -> None:
    response = appeal(http, start(http, sub=JULIANA.customer_id), JULIANA.customer_id)
    assert (response.status_code, response.json()) == (409, {"error": "case_not_appealable"})


def test_another_customers_case_cannot_be_appealed(http: TestClient) -> None:
    response = appeal(http, start(http, sub=MARIANA), JUAN.customer_id)
    assert (response.status_code, response.json()) == (404, {"error": "not_found"})
