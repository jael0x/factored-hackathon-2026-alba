from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any, get_args

import psycopg
import pytest
from fastapi.testclient import TestClient

from api.application.cycle.ports import TurnRequest
from api.contract_models import CloseOutcome, EndReason
from api.domain.policy.templates import certificate_for_close, certificate_for_policy, render_notice
from api.domain.process.events import ANALYSIS_COMPLETED
from api.infrastructure.config.settings import settings
from api.infrastructure.mail.smtp import get_mailer
from api.main import create_app
from api.tests.chat_harness import (
    AS_OF,
    CARD_ES,
    alicia_packet,
    alicia_queue_item,
    case_body,
    post_as,
    reset,
    shape,
    start_body,
)
from api.tests.cycle_harness import ALICIA, JUAN, JULIANA, MARIANA, ScriptedModel, query, scripted
from api.tests.login_harness import FakeMailer, Harness, Login, consultant_login, customer_login
from api.tests.oracle import ORACLE, OracleCustomer, OracleResult, oracle_customer, seed_oracle_profiles
from api.tests.turn_harness import load_turn_fixture

pytestmark = pytest.mark.integration

ORACLE_TEST_DB = "alba_oracle_test"
CESAR_EMAIL = "cesar.gonzalez@example.com"
JULIANA_INCOME = load_turn_fixture("es-gano-45000-pesos").text
STILL_WAITING = "¿ya revisaron mi caso?"
NEEDS_INCOME = render_notice("needs_income", "es", "credit_card")
ALICIA_OPENING = [("customer", CARD_ES), ("template", render_notice("refer_notice", "es", "credit_card"))]

# ARCHITECTURE.md, "What gets built": the four outcomes. Written here, not read from the fixture, so a fixture edit
# that moves an outcome turns this file red instead of moving the expectation with it.
CONTRACT_TABLE = {
    JUAN: OracleResult(outcome="PREQUALIFIED", deciding_rule="R05", state="ended", end_reason="prequalified"),
    JULIANA: OracleResult(outcome="NEEDS_INFO", deciding_rule="R06", state="ai_active", end_reason=None),
    ALICIA: OracleResult(outcome="REFER", deciding_rule="R05", state="human_active", end_reason=None),
    MARIANA: OracleResult(
        outcome="NOT_PREQUALIFIED", deciding_rule="R02", state="ended", end_reason="not_prequalified"
    ),
}
PASSED_TO_R05 = [("R01", "passed"), ("R02", "passed"), ("R03", "passed"), ("R09", "passed"), ("R04", "passed")]
END_REASON: dict[CloseOutcome, EndReason] = {"PREQUALIFIED": "prequalified", "NOT_PREQUALIFIED": "not_prequalified"}


@dataclass
class Bank:
    http: TestClient
    mail: FakeMailer
    model: ScriptedModel


def document_of(customer: OracleCustomer) -> str:
    return f"ORACLE-{customer.customer_id}"


def email_of(customer: OracleCustomer) -> str | None:
    return f"{customer.customer_id.lower()}@example.com" if customer.has_email else None


def seed_oracle_people(url: str) -> None:
    cesar = ORACLE.consultant
    with psycopg.connect(url) as conn:
        conn.cursor().executemany(
            """
            INSERT INTO customers (customer_id, document_number, first_name, last_name, email, country, segment,
                                   customer_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [
                (
                    c.customer_id,
                    document_of(c),
                    c.first_name,
                    c.last_name,
                    email_of(c),
                    c.country,
                    c.segment,
                    c.customer_status,
                )
                for c in ORACLE.customers
            ],
        )
        seed_oracle_profiles(conn)
        conn.execute(
            """
            INSERT INTO service_agents (agent_id, employee_code, first_name, last_name, email, agent_status, specialty)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                cesar.consultant_id,
                cesar.employee_code,
                cesar.first_name,
                cesar.last_name,
                CESAR_EMAIL,
                cesar.status,
                cesar.specialty,
            ),
        )


@pytest.fixture(scope="module")
def oracle_database(migrated_database: Callable[[str], str]) -> str:
    url = migrated_database(ORACLE_TEST_DB)
    seed_oracle_people(url)
    return url


@pytest.fixture
def bank(oracle_database: str, monkeypatch: pytest.MonkeyPatch) -> Iterator[Bank]:
    reset(oracle_database)
    with psycopg.connect(oracle_database) as conn:
        conn.execute("DELETE FROM login_codes")
    monkeypatch.setattr(settings, "database_url", oracle_database)
    monkeypatch.setattr(settings, "run_worker", True)
    model = scripted("es-gano-45000-pesos")
    mail = FakeMailer()
    app = create_app(lambda: model)
    app.dependency_overrides[get_mailer] = lambda: mail
    with TestClient(app) as client:
        yield Bank(client, mail, model)


def sign_in(bank: Bank, login: Login) -> dict[str, str]:
    harness = Harness(http=bank.http, mail=bank.mail)
    harness.request_code(login)
    return {"Authorization": f"Bearer {harness.token(login, harness.last_code())}"}


def customer(bank: Bank, customer_id: str) -> dict[str, str]:
    return sign_in(bank, customer_login(document_of(oracle_customer(customer_id))))


def cesar(bank: Bank) -> dict[str, str]:
    return sign_in(bank, consultant_login(CESAR_EMAIL, ORACLE.consultant.employee_code))


def start_card(bank: Bank, session: dict[str, str]) -> dict[str, Any]:
    return post_as(bank.http, start_body("credit_card", "es", CARD_ES, None), session)


def say(bank: Bank, case: dict[str, Any], text: str, session: dict[str, str]) -> dict[str, Any]:
    return post_as(bank.http, case_body(case, text), session)


def read(bank: Bank, path: str, session: dict[str, str]) -> Any:
    response = bank.http.get(path, headers=session)
    assert response.status_code == 200, response.text
    return response.json()


def analyses(bank: Bank, case: dict[str, Any], consultant: dict[str, str]) -> list[dict[str, Any]]:
    events = read(bank, f"/consultant/case/{case['process_id']}/trace", consultant)["events"]
    return [event for event in events if event["event_name"] == ANALYSIS_COMPLETED]


def decided(analysis: dict[str, Any]) -> tuple[str, str, str, list[tuple[str, str]]]:
    steps = [(step["rule_id"], step["result"]) for step in analysis["rule_trace"]]
    return analysis["outcome"], analysis["deciding_rule"], analysis["policy_version"], steps


def queue(bank: Bank, consultant: dict[str, str]) -> list[dict[str, Any]]:
    cases = read(bank, "/consultant/queue", consultant)["cases"]
    assert isinstance(cases, list)
    return cases


def certificate_of(case: dict[str, Any], **fields: Any) -> dict[str, Any]:
    return {"event_id": case["messages"][-1]["event_id"], "locale": "es", "product": "credit_card", **fields}


def test_the_fixture_expects_the_outcomes_the_contract_table_names() -> None:
    assert {c.customer_id: c.expected for c in ORACLE.customers} == CONTRACT_TABLE


def test_juan_prequalifies_by_r05_without_a_model_call_and_never_reaches_a_person(bank: Bank) -> None:
    case = start_card(bank, customer(bank, JUAN))
    body = certificate_for_policy("PREQUALIFIED", "es", "credit_card")
    assert shape(case) == (
        "ended",
        "prequalified",
        "credit_card",
        "es",
        False,
        [("customer", CARD_ES), ("template", body)],
    )
    assert case["certificate"] == certificate_of(
        case,
        decided_by="policy",
        outcome="PREQUALIFIED",
        body=body,
        income_local=306753.45,
        income_currency="MXN",
        income_usd=17988.32906145,
        as_of=AS_OF,
    )
    consultant = cesar(bank)
    assert [decided(a) for a in analyses(bank, case, consultant)] == [
        ("PREQUALIFIED", "R05", "alba-credit-v1", [*PASSED_TO_R05, ("R06", "passed"), ("R05", "PREQUALIFIED")])
    ]
    assert queue(bank, consultant) == []
    assert bank.model.calls == []


def test_juliana_is_asked_her_income_by_r06_and_prequalifies_by_r05_once_she_states_it(
    bank: Bank, oracle_database: str
) -> None:
    session = customer(bank, JULIANA)
    asked = start_card(bank, session)
    opening = [("customer", CARD_ES), ("template", NEEDS_INCOME)]
    assert shape(asked) == ("ai_active", None, "credit_card", "es", False, opening)
    assert asked["certificate"] is None
    assert bank.model.calls == []

    answered = say(bank, asked, JULIANA_INCOME, session)
    body = certificate_for_policy("PREQUALIFIED", "es", "credit_card")
    assert shape(answered) == (
        "ended",
        "prequalified",
        "credit_card",
        "es",
        False,
        [*opening, ("customer", JULIANA_INCOME), ("template", body)],
    )
    assert answered["certificate"] == certificate_of(
        answered,
        decided_by="policy",
        outcome="PREQUALIFIED",
        body=body,
        income_local=45000,
        income_currency="MXN",
        income_usd=None,
        as_of=AS_OF,
    )
    assert bank.model.calls == [
        TurnRequest(
            text=JULIANA_INCOME,
            locale="es",
            process_state="ai_active",
            income_on_file=False,
            score_on_file=True,
            has_active_card=False,
            has_active_personal_loan=False,
        )
    ]
    consultant = cesar(bank)
    assert [decided(a) for a in analyses(bank, answered, consultant)] == [
        ("NEEDS_INFO", "R06", "alba-credit-v1", [*PASSED_TO_R05, ("R06", "NEEDS_INFO")]),
        ("PREQUALIFIED", "R05", "alba-credit-v1", [*PASSED_TO_R05, ("R06", "self_declared"), ("R05", "PREQUALIFIED")]),
    ]
    assert queue(bank, consultant) == []
    sql = "SELECT income_local, income_usd FROM customer_credit_profile WHERE customer_id = %s"
    assert query(oracle_database, sql, (JULIANA,)) == [(None, None)]


def test_alicia_is_referred_by_r05_and_waits_for_cesar_without_a_model_call(bank: Bank) -> None:
    session = customer(bank, ALICIA)
    referred = start_card(bank, session)
    assert shape(referred) == ("human_active", None, "credit_card", "es", False, ALICIA_OPENING)
    assert referred["certificate"] is None

    consultant = cesar(bank)
    assert [decided(a) for a in analyses(bank, referred, consultant)] == [
        ("REFER", "R05", "alba-credit-v1", [*PASSED_TO_R05, ("R06", "passed"), ("R05", "REFER")])
    ]
    assert queue(bank, consultant) == [alicia_queue_item(referred)]
    assert read(bank, f"/consultant/case/{referred['process_id']}", consultant) == alicia_packet(referred)

    waiting = say(bank, referred, STILL_WAITING, session)
    assert shape(waiting) == (
        "human_active",
        None,
        "credit_card",
        "es",
        False,
        [*ALICIA_OPENING, ("customer", STILL_WAITING)],
    )
    assert bank.model.calls == []


@pytest.mark.parametrize("outcome", get_args(CloseOutcome))
def test_cesar_closes_alicias_case_with_either_outcome_and_she_gets_his_certificate(
    bank: Bank, outcome: CloseOutcome
) -> None:
    session = customer(bank, ALICIA)
    referred = start_card(bank, session)
    consultant = cesar(bank)
    closing = bank.http.post(
        f"/consultant/case/{referred['process_id']}/close", json={"outcome": outcome}, headers=consultant
    )
    end_reason = END_REASON[outcome]
    assert (closing.status_code, closing.json()) == (
        200,
        {"process_id": referred["process_id"], "state": "ended", "end_reason": end_reason, "outcome": outcome},
    )
    closed = read(bank, f"/case/{referred['process_id']}", session)
    body = certificate_for_close(outcome, "es", "credit_card")
    assert shape(closed) == ("ended", end_reason, "credit_card", "es", False, [*ALICIA_OPENING, ("template", body)])
    assert closed["certificate"] == certificate_of(
        closed,
        decided_by="consultant",
        outcome=outcome,
        body=body,
        income_local=None,
        income_currency=None,
        income_usd=None,
        as_of=None,
    )
    assert queue(bank, consultant) == []
    assert bank.model.calls == []


def test_mariana_does_not_prequalify_by_r02_before_her_card_or_score_is_read(bank: Bank) -> None:
    case = start_card(bank, customer(bank, MARIANA))
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
    consultant = cesar(bank)
    assert [decided(a) for a in analyses(bank, case, consultant)] == [
        ("NOT_PREQUALIFIED", "R02", "alba-credit-v1", [("R01", "passed"), ("R02", "NOT_PREQUALIFIED")])
    ]
    assert queue(bank, consultant) == []
    assert bank.model.calls == []
