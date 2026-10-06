import threading
from datetime import date
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from api.application.consultants.cases import CaseAlreadyClosed, close_consultant_case
from api.contract_models import CloseOutcome, EndReason, Locale
from api.domain.policy.engine import CreditProfile, decide
from api.domain.policy.templates import certificate_for_close
from api.domain.process.events import transition_key
from api.domain.process.lifecycle import ProcessRow
from api.domain.process.new_events import Cause, analysis_completed, thread_taken
from api.infrastructure.db.consultant_cases import PostgresConsultantCases
from api.infrastructure.db.events import PostgresEvents
from api.infrastructure.db.json_codec import configure_json
from api.tests.chat_harness import CARD_ES, CESAR, appeal, bearer, close, say, start
from api.tests.cycle_harness import MARIANA, planning, wait_until_blocked
from api.tests.login_harness import ALICIA, JUAN, JULIANA, NO_EMAIL

pytestmark = pytest.mark.integration

CONSULTANT = bearer(CESAR, "consultant")
FORBIDDEN = (403, {"error": "forbidden"})
UNAUTHORIZED = (401, {"error": "unauthorized"})
NOT_FOUND = (404, {"error": "not_found"})
ALREADY_CLOSED = (409, {"error": "already_closed"})
NOT_CLOSABLE = (409, {"error": "case_not_closable"})
INVALID = (422, {"error": "invalid_body"})
AS_OF = "2026-06-17"


def referred(http: TestClient, locale: Locale = "es") -> dict[str, Any]:
    return start(http, sub=ALICIA.customer_id, locale=locale)


def queue(http: TestClient) -> list[dict[str, Any]]:
    response = http.get("/consultant/queue", headers=CONSULTANT)
    assert response.status_code == 200, response.text
    cases = response.json()["cases"]
    assert isinstance(cases, list)
    return cases


def queued_ids(http: TestClient) -> list[str]:
    return [item["process_id"] for item in queue(http)]


def packet(http: TestClient, case: dict[str, Any]) -> Any:
    return http.get(f"/consultant/case/{case['process_id']}", headers=CONSULTANT)


def trace(http: TestClient, case: dict[str, Any]) -> list[dict[str, Any]]:
    response = http.get(f"/consultant/case/{case['process_id']}/trace", headers=CONSULTANT)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["process_id"] == case["process_id"]
    events = body["events"]
    assert isinstance(events, list)
    return events


def answer(response: Any) -> tuple[int, Any]:
    return response.status_code, response.json()


def event_count(url: str) -> int:
    with psycopg.connect(url) as conn:
        row = conn.execute("SELECT count(*) FROM events").fetchone()
    assert row is not None
    return int(row[0])


def set_opened_at(url: str, case: dict[str, Any], opened_at: str) -> None:
    with psycopg.connect(url) as conn:
        conn.execute("UPDATE processes SET created_at = %s WHERE id = %s", (opened_at, case["process_id"]))


def alicia_packet(case: dict[str, Any], locale: Locale = "es") -> dict[str, Any]:
    return {
        "process_id": case["process_id"],
        "state": "human_active",
        "customer_id": ALICIA.customer_id,
        "first_name": "Alicia Mariana",
        "last_name": "Parra Álvarez",
        "product": "credit_card",
        "credit_score": 615,
        "income_local": 4707334.28,
        "income_currency": "COP",
        "income_usd": 1167.41890144,
        "deciding_rule": "R05",
        "policy_version": "alba-credit-v1",
        "outcome": "REFER",
        "reason_code": "policy_refer",
        "locale": locale,
        "closable": True,
    }


def test_the_review_queue_lists_only_the_cases_waiting_for_a_person(http: TestClient) -> None:
    start(http, sub=JUAN.customer_id)
    start(http, sub=MARIANA)
    alicia = referred(http)
    assert queue(http) == [
        {
            "process_id": alicia["process_id"],
            "customer_id": ALICIA.customer_id,
            "first_name": "Alicia Mariana",
            "last_name": "Parra Álvarez",
            "product": "credit_card",
            "reason_code": "policy_refer",
            "locale": "es",
        }
    ]


def test_the_queue_follows_when_each_case_was_opened_before_its_id(http: TestClient, chat_database: str) -> None:
    alicia = referred(http)
    juliana = say(http, start(http, sub=JULIANA.customer_id), "quiero hablar con una persona", JULIANA.customer_id)
    first, later = sorted([alicia, juliana], key=lambda case: UUID(case["process_id"]), reverse=True)
    set_opened_at(chat_database, first, "2026-10-05T09:00:00Z")
    set_opened_at(chat_database, later, "2026-10-05T10:00:00Z")
    assert queued_ids(http) == [first["process_id"], later["process_id"]]


def test_cases_opened_at_the_same_instant_are_ordered_by_id(http: TestClient, chat_database: str) -> None:
    alicia = referred(http)
    juliana = say(http, start(http, sub=JULIANA.customer_id), "quiero hablar con una persona", JULIANA.customer_id)
    for case in (alicia, juliana):
        set_opened_at(chat_database, case, "2026-10-05T10:00:00Z")
    assert queued_ids(http) == sorted([alicia["process_id"], juliana["process_id"]], key=UUID)


def test_the_case_shows_the_handoff_packet(http: TestClient) -> None:
    case = referred(http)
    assert answer(packet(http, case)) == (200, alicia_packet(case))


def test_a_case_the_policy_left_without_a_result_cannot_be_closed(http: TestClient, chat_database: str) -> None:
    asked = start(http, sub=JULIANA.customer_id)
    case = say(http, asked, "quiero hablar con una persona", JULIANA.customer_id)
    assert answer(packet(http, case)) == (
        200,
        {
            "process_id": case["process_id"],
            "state": "human_active",
            "customer_id": JULIANA.customer_id,
            "first_name": "Juliana",
            "last_name": "Castro Gómez",
            "product": "credit_card",
            "credit_score": 714,
            "income_local": None,
            "income_currency": "MXN",
            "income_usd": None,
            "deciding_rule": "R06",
            "policy_version": "alba-credit-v1",
            "outcome": "NEEDS_INFO",
            "reason_code": "customer_requested_human",
            "locale": "es",
            "closable": False,
        },
    )
    written = event_count(chat_database)
    assert answer(close(http, case, "PREQUALIFIED")) == NOT_CLOSABLE
    assert event_count(chat_database) == written
    assert queued_ids(http) == [case["process_id"]]


def test_a_case_handed_off_before_the_policy_ran_shows_no_analysis_and_cannot_be_closed(http: TestClient) -> None:
    case = start(http, sub=NO_EMAIL.customer_id)
    status, body = answer(packet(http, case))
    assert status == 200
    analysis = ["product", "credit_score", "income_local", "income_currency", "income_usd", "deciding_rule"]
    assert [body[name] for name in [*analysis, "policy_version", "outcome", "reason_code", "closable"]] == [
        *[None] * len(analysis),
        None,
        None,
        "tool_failed",
        False,
    ]
    assert answer(close(http, case, "NOT_PREQUALIFIED")) == NOT_CLOSABLE


# Recorded straight into the store, with no commands planned, so the case holds two of each fact.
def test_the_packet_and_the_queue_read_the_latest_analysis_and_the_latest_handoff(
    http: TestClient, chat_database: str
) -> None:
    case = referred(http)
    process = ProcessRow(UUID(case["process_id"]), ALICIA.customer_id, "human_active")
    no_income = CreditProfile("Active", 615, None, "COP", None, 0, False, False, date(2026, 6, 17))
    cause = Cause(event_id=uuid4(), command_id=None)
    with psycopg.connect(chat_database) as conn:
        configure_json(conn)
        events = PostgresEvents(conn)
        events.append(analysis_completed(process, decide(no_income, "credit_card", None), "credit_card", "es", cause))
        move = transition_key(process.process_id, "human_active", cause.event_id)
        events.append(thread_taken(process, "tool_failed", move, cause))
    status, body = answer(packet(http, case))
    assert (status, body["outcome"], body["deciding_rule"], body["reason_code"], body["closable"]) == (
        200,
        "NEEDS_INFO",
        "R06",
        "tool_failed",
        False,
    )
    assert [item["reason_code"] for item in queue(http)] == ["tool_failed"]


def test_only_a_case_with_a_person_has_a_packet(http: TestClient) -> None:
    ended = start(http, sub=JUAN.customer_id)
    asked = start(http, sub=JULIANA.customer_id)
    unknown = {"process_id": str(uuid4())}
    assert [answer(packet(http, case)) for case in (ended, asked, unknown)] == [NOT_FOUND] * 3


def test_the_trace_lists_the_case_events_in_the_order_they_happened(http: TestClient) -> None:
    case = referred(http)
    events = trace(http, case)
    assert [(e["event_name"], e["actor"], e["process_state"]) for e in events] == [
        ("conversation.message_received", "customer", "ai_active"),
        ("process.started", "system", "ai_active"),
        ("analysis.completed", "system", "ai_active"),
        ("conversation.template_sent", "system", "ai_active"),
        ("process.state_changed", "system", "human_active"),
        ("conversation.thread_taken", "system", "human_active"),
    ]
    message, started, analysis, notice, moved, taken = events
    assert (message["process_id"], message["text"], message["product"]) == (None, CARD_ES, "credit_card")
    assert (started["process_id"], started["process_key"], started["caused_by_event_id"]) == (
        case["process_id"],
        "credit_prequalification",
        message["id"],
    )
    assert (analysis["outcome"], analysis["deciding_rule"], analysis["policy_version"]) == (
        "REFER",
        "R05",
        "alba-credit-v1",
    )
    assert notice["template_id"] == "refer_notice"
    assert (moved["from_state"], moved["to_state"], moved["end_reason"]) == ("ai_active", "human_active", None)
    assert taken["reason_code"] == "policy_refer"


def test_the_trace_shows_the_facts_behind_the_decision(http: TestClient) -> None:
    [analysis] = [e for e in trace(http, referred(http)) if e["event_name"] == "analysis.completed"]
    assert analysis["facts"] == [
        {"name": "credit_score", "value": 615, "source": "customer_credit_profile.credit_score", "as_of": AS_OF},
        {"name": "income_local", "value": 4707334.28, "source": "customer_credit_profile.income_local", "as_of": AS_OF},
        {
            "name": "income_currency",
            "value": "COP",
            "source": "customer_credit_profile.income_currency",
            "as_of": AS_OF,
        },
        {"name": "income_usd", "value": 1167.41890144, "source": "customer_credit_profile.income_usd", "as_of": AS_OF},
    ]


def test_a_message_written_while_the_case_waits_for_a_person_is_recorded_and_not_classified(http: TestClient) -> None:
    case = referred(http)
    say(http, case, "¿ya revisaron mi caso?", ALICIA.customer_id)
    events = trace(http, case)
    assert (events[-1]["event_name"], events[-1]["text"], events[-1]["process_state"]) == (
        "conversation.message_received",
        "¿ya revisaron mi caso?",
        "human_active",
    )
    assert "conversation.turn_classified" not in [e["event_name"] for e in events]


def test_an_unknown_case_has_no_trace(http: TestClient) -> None:
    response = http.get(f"/consultant/case/{uuid4()}/trace", headers=CONSULTANT)
    assert answer(response) == NOT_FOUND


@pytest.mark.parametrize(
    ("outcome", "end_reason"), [("PREQUALIFIED", "prequalified"), ("NOT_PREQUALIFIED", "not_prequalified")]
)
def test_closing_the_case_sends_the_customer_the_outcome(
    http: TestClient, outcome: CloseOutcome, end_reason: EndReason
) -> None:
    case = referred(http)
    assert answer(close(http, case, outcome)) == (
        200,
        {"process_id": case["process_id"], "state": "ended", "end_reason": end_reason, "outcome": outcome},
    )
    closed = http.get(f"/case/{case['process_id']}", headers=bearer(ALICIA.customer_id)).json()
    assert (closed["state"], closed["end_reason"], closed["certificate"]["decided_by"]) == (
        "ended",
        end_reason,
        "consultant",
    )
    assert closed["messages"][-1] == {
        "id": closed["messages"][-1]["id"],
        "author": "template",
        "body": certificate_for_close(outcome, "es", "credit_card"),
        "event_id": closed["certificate"]["event_id"],
    }
    assert queue(http) == []
    names = [e["event_name"] for e in trace(http, case)]
    assert (names.count("analysis.completed"), names.count("conversation.consultant_closed")) == (1, 1)
    [closing] = [e for e in trace(http, case) if e["event_name"] == "conversation.consultant_closed"]
    assert (closing["actor"], closing["consultant_id"], closing["outcome"]) == ("consultant", CESAR, outcome)


def test_the_outcome_is_written_in_the_customers_language_not_the_consultants(http: TestClient) -> None:
    case = referred(http, locale="pt")
    assert answer(packet(http, case)) == (200, alicia_packet(case, locale="pt"))
    assert close(http, case, "PREQUALIFIED").status_code == 200
    closed = http.get(f"/case/{case['process_id']}", headers=bearer(ALICIA.customer_id)).json()
    assert (closed["certificate"]["locale"], closed["certificate"]["body"]) == (
        "pt",
        certificate_for_close("PREQUALIFIED", "pt", "credit_card"),
    )


def test_a_closed_case_cannot_be_closed_again(http: TestClient, chat_database: str) -> None:
    case = referred(http)
    assert close(http, case, "NOT_PREQUALIFIED").status_code == 200
    written = event_count(chat_database)
    assert answer(close(http, case, "PREQUALIFIED")) == ALREADY_CLOSED
    assert answer(close(http, case, "NOT_PREQUALIFIED")) == ALREADY_CLOSED
    closed = http.get(f"/case/{case['process_id']}", headers=bearer(ALICIA.customer_id)).json()
    assert (closed["end_reason"], closed["certificate"]["outcome"]) == ("not_prequalified", "NOT_PREQUALIFIED")
    assert event_count(chat_database) == written


@pytest.mark.parametrize("body", [{"outcome": "REFER"}, {"outcome": "PREQUALIFIED", "text": "Aprobado"}, {}])
def test_the_consultant_cannot_close_with_any_other_body(
    http: TestClient, chat_database: str, body: dict[str, str]
) -> None:
    case = referred(http)
    written = event_count(chat_database)
    response = http.post(f"/consultant/case/{case['process_id']}/close", json=body, headers=CONSULTANT)
    assert answer(response) == INVALID
    assert (event_count(chat_database), queued_ids(http)) == (written, [case["process_id"]])


def test_a_case_not_with_a_person_is_not_found_and_an_ended_one_is_already_closed(http: TestClient) -> None:
    asked = start(http, sub=JULIANA.customer_id)
    ended = start(http, sub=JUAN.customer_id)
    unknown = {"process_id": str(uuid4())}
    answers = [answer(close(http, case, "PREQUALIFIED")) for case in (asked, unknown, ended)]
    assert answers == [NOT_FOUND, NOT_FOUND, ALREADY_CLOSED]


def test_an_appealed_no_is_closable_and_the_consultant_decides_it(http: TestClient) -> None:
    decided = start(http, sub=MARIANA)
    assert appeal(http, decided, MARIANA).status_code == 200
    status, body = answer(packet(http, decided))
    assert (status, body["outcome"], body["deciding_rule"], body["reason_code"], body["closable"]) == (
        200,
        "NOT_PREQUALIFIED",
        "R02",
        "customer_requested_human",
        True,
    )
    assert answer(close(http, decided, "PREQUALIFIED"))[1]["end_reason"] == "prequalified"
    closed = http.get(f"/case/{decided['process_id']}", headers=bearer(MARIANA)).json()
    assert (closed["certificate"]["decided_by"], closed["certificate"]["outcome"]) == ("consultant", "PREQUALIFIED")


# A case from before D24 has no product, so the consultant's certificate cannot be written.
def test_a_close_whose_certificate_cannot_be_written_fails_loud_and_the_case_stays_with_a_person(
    http: TestClient, chat_database: str
) -> None:
    case = referred(http)
    with psycopg.connect(chat_database) as conn:
        conn.execute("UPDATE processes SET product = NULL WHERE id = %s", (case["process_id"],))
    with pytest.raises(LookupError, match="settled but did not end it as prequalified"):
        close(http, case, "PREQUALIFIED")
    assert answer(close(http, case, "PREQUALIFIED")) == ALREADY_CLOSED
    assert queued_ids(http) == [case["process_id"]]


def test_of_two_closes_at_once_only_one_is_written(http: TestClient, chat_database: str) -> None:
    process_id = UUID(referred(http)["process_id"])
    refused: list[Exception] = []
    with psycopg.connect(chat_database) as first, psycopg.connect(chat_database) as second:
        configure_json(first)
        configure_json(second)
        close_consultant_case(planning(first), PostgresConsultantCases(first), CESAR, process_id, "PREQUALIFIED")

        def close_second() -> None:
            try:
                cases = PostgresConsultantCases(second)
                close_consultant_case(planning(second), cases, CESAR, process_id, "NOT_PREQUALIFIED")
            except CaseAlreadyClosed as error:
                refused.append(error)

        racing = threading.Thread(target=close_second)
        racing.start()
        wait_until_blocked(chat_database, second.info.backend_pid)
        first.commit()
        racing.join(timeout=10)
    assert not racing.is_alive()
    assert [type(error) for error in refused] == [CaseAlreadyClosed]
    with psycopg.connect(chat_database) as conn:
        rows = conn.execute(
            "SELECT payload->>'outcome' FROM events WHERE event_name = 'conversation.consultant_closed'"
        ).fetchall()
    assert rows == [("PREQUALIFIED",)]


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/consultant/queue"),
        ("GET", "/consultant/case/{process_id}"),
        ("GET", "/consultant/case/{process_id}/trace"),
        ("POST", "/consultant/case/{process_id}/close"),
    ],
)
def test_the_consultant_routes_refuse_a_customer_and_a_missing_session(
    http: TestClient, chat_database: str, method: str, path: str
) -> None:
    case = referred(http)
    url = path.format(process_id=case["process_id"])
    body = {"outcome": "PREQUALIFIED"} if method == "POST" else None
    written = event_count(chat_database)
    as_customer = http.request(method, url, json=body, headers=bearer(ALICIA.customer_id))
    without_session = http.request(method, url, json=body)
    assert [answer(as_customer), answer(without_session)] == [FORBIDDEN, UNAUTHORIZED]
    assert event_count(chat_database) == written
