from collections.abc import Callable, Iterator
from decimal import Decimal
from typing import Any, get_args
from uuid import UUID, uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg_pool import ConnectionPool

from api.application.cycle.attempt import Done, Failed, Retried
from api.application.cycle.ports import ReadTurn
from api.application.processes import InCase, StartCase
from api.contract_models import Locale, ProductKey
from api.domain.policy.templates import certificate_for_close, certificate_for_policy, render_notice
from api.domain.process.commands import GENERATE_COMMAND, hand_off
from api.domain.process.events import ANALYSIS_COMPLETED
from api.domain.process.lifecycle import CUSTOMER_REQUESTED_HUMAN, MessageStamp, ProcessRow, parse_state
from api.domain.process.new_events import AlreadyAppended, appeal_requested, consultant_closed, message_received
from api.domain.process.rules import PlannedCommand, command_key
from api.domain.process.turns import ShownReading, TurnReading, WithheldReading
from api.infrastructure.config.settings import settings
from api.infrastructure.db.commands import PostgresCommands
from api.infrastructure.db.events import PostgresEventLog, PostgresEvents
from api.infrastructure.db.json_codec import configure_json
from api.infrastructure.db.processes import PostgresProcesses
from api.infrastructure.db.profile import PostgresProfiles
from api.infrastructure.llm.keywords import B0_MODEL, read_keyword_turn
from api.infrastructure.llm.schema import reading_of
from api.main import app
from api.presentation.worker import loop
from api.presentation.worker.loop import Worker, model_not_built, read_turn_for, run_next, run_until_idle
from api.tests.cycle_harness import (
    ALICIA,
    JUAN,
    JULIANA,
    MARIANA,
    NO_PROFILE,
    ScriptedModel,
    append,
    cycle_pool,
    query,
    scripted,
    seed_cycle_people,
    send,
)
from api.tests.oracle import ORACLE, OracleCustomer
from api.tests.turn_harness import load_turn_fixture

pytestmark = pytest.mark.integration

WORKER_TEST_DB = "alba_worker_test"
CARD = "quiero una tarjeta de crédito"
OPENING: dict[ProductKey, str] = {
    "credit_card": "Quiero saber si precalifico para una tarjeta de crédito.",
    "personal_loan": "Quiero saber si precalifico para un préstamo personal.",
}
LOAN = "quiero un préstamo personal"
HUMAN = "quiero hablar con una persona"
INCOME = "gano 45,000 pesos al mes"
COLOMBIAN_INCOME = "gano 45,000 pesos colombianos"
CESAR = "AGT-OJ9N4FGYV9"
AS_OF = "2026-06-17"
MODEL_DOWN = "ModelDown: the model did not answer"

# A case starts from a product on the home, with the consent already given (PLAN.md D24): the policy runs at once.
START = ["conversation.message_received", "process.started", "analysis.completed"]
NOTICE = [*START, "conversation.template_sent"]
ANSWER = ["conversation.message_received", "conversation.turn_classified"]
POLICY_END = ["prequalification.decided", "process.state_changed", "process.ended"]
HANDOFF = ["process.state_changed", "conversation.thread_taken"]


@pytest.fixture(scope="module")
def worker_database(migrated_database: Callable[[str], str]) -> str:
    url = migrated_database(WORKER_TEST_DB)
    seed_cycle_people(url)
    return url


@pytest.fixture
def url(worker_database: str) -> str:
    with psycopg.connect(worker_database) as conn:
        conn.execute("TRUNCATE events, messages, processes, commands")
    return worker_database


@pytest.fixture
def pool(url: str) -> Iterator[ConnectionPool]:
    with cycle_pool(url) as opened:
        yield opened


# Rows come back as plain tuples and payloads as decoded JSON, so each assertion compares the whole stored fact.
def names(url: str, customer_id: str) -> list[str]:
    rows = query(url, "SELECT event_name FROM events WHERE customer_id = %s ORDER BY seq", (customer_id,))
    return [row[0] for row in rows]


def cases(url: str, customer_id: str) -> list[tuple[Any, ...]]:
    sql = "SELECT state, end_reason, product, locale FROM processes WHERE customer_id = %s ORDER BY created_at, id"
    return query(url, sql, (customer_id,))


def thread(url: str, customer_id: str) -> list[tuple[Any, ...]]:
    return query(
        url,
        """
        SELECT m.author, m.body
        FROM messages m JOIN events e ON e.id = m.event_id JOIN processes p ON p.id = m.process_id
        WHERE p.customer_id = %s
        ORDER BY e.seq
        """,
        (customer_id,),
    )


def queue(url: str) -> list[tuple[Any, ...]]:
    sql = "SELECT command_name, emitted_by_rule_id, status, attempt_count, last_error FROM commands ORDER BY seq"
    return query(url, sql)


def payloads(url: str, customer_id: str, event_name: str) -> list[Any]:
    sql = "SELECT payload FROM events WHERE customer_id = %s AND event_name = %s ORDER BY seq"
    return [row[0] for row in query(url, sql, (customer_id, event_name))]


def open_case_of(url: str, customer_id: str) -> ProcessRow:
    sql = "SELECT id, state FROM processes WHERE customer_id = %s AND state <> 'ended'"
    [(process_id, state)] = query(url, sql, (customer_id,))
    return ProcessRow(process_id, customer_id, parse_state(state))


def done(name: str, rule: str, attempts: int = 1) -> tuple[Any, ...]:
    return (name, rule, "done", attempts, None)


def facts(score: int, income: Decimal | None, currency: str, usd: Decimal | None, source: str) -> list[Any]:
    return [
        {"name": "credit_score", "value": score, "source": "customer_credit_profile.credit_score", "as_of": AS_OF},
        {"name": "income_local", "value": income, "source": source, "as_of": AS_OF},
        {
            "name": "income_currency",
            "value": currency,
            "source": "customer_credit_profile.income_currency",
            "as_of": AS_OF,
        },
        {"name": "income_usd", "value": usd, "source": "customer_credit_profile.income_usd", "as_of": AS_OF},
    ]


def start(
    pool: ConnectionPool,
    customer_id: str,
    product: ProductKey = "credit_card",
    locale: Locale = "es",
    message_id: UUID | None = None,
) -> UUID:
    return send(pool, customer_id, OPENING[product], StartCase(product), locale, message_id)


def say(url: str, pool: ConnectionPool, customer_id: str, text: str) -> UUID:
    return send(pool, customer_id, text, InCase(open_case_of(url, customer_id).process_id))


def converse(url: str, pool: ConnectionPool, customer_id: str, model: ReadTurn, *texts: str) -> None:
    for text in texts:
        say(url, pool, customer_id, text)
        run_until_idle(pool, model)


def started(pool: ConnectionPool, customer_id: str, product: ProductKey = "credit_card") -> None:
    start(pool, customer_id, product)
    run_until_idle(pool, scripted())


@pytest.mark.parametrize("customer", ORACLE.customers, ids=lambda c: c.customer_id)
@pytest.mark.parametrize("product", get_args(ProductKey))
def test_each_oracle_case_reaches_its_outcome_and_state(
    url: str, pool: ConnectionPool, customer: OracleCustomer, product: ProductKey
) -> None:
    started(pool, customer.customer_id, product)
    expected = customer.expected
    [analysis] = payloads(url, customer.customer_id, ANALYSIS_COMPLETED)
    assert (analysis["outcome"], analysis["deciding_rule"]) == (expected.outcome, expected.deciding_rule)
    assert cases(url, customer.customer_id) == [(expected.state, expected.end_reason, product, "es")]


def test_juan_prequalifies_for_a_card_from_the_home_without_a_model_call(url: str, pool: ConnectionPool) -> None:
    model = scripted()
    start(pool, JUAN)
    assert run_until_idle(pool, model) == [Done(1), Done(1), Done(1), Done(1)]
    assert names(url, JUAN) == [*START, *POLICY_END]
    assert cases(url, JUAN) == [("ended", "prequalified", "credit_card", "es")]
    assert thread(url, JUAN) == [("template", certificate_for_policy("PREQUALIFIED", "es", "credit_card"))]
    assert queue(url) == [
        done("process.start", "open_process"),
        done("policy.run", "run_requested_policy"),
        done("decision.render", "render_decision"),
        done("process.end", "end_after_decision"),
    ]
    [analysis] = payloads(url, JUAN, "analysis.completed")
    assert (analysis["outcome"], analysis["deciding_rule"], analysis["locale"]) == ("PREQUALIFIED", "R05", "es")
    file_income = "customer_credit_profile.income_local"
    assert analysis["facts"] == facts(812, Decimal("306753.45"), "MXN", Decimal("17988.32906145"), file_income)
    assert payloads(url, JUAN, "process.ended") == [{"end_reason": "prequalified", "policy_version": "alba-credit-v1"}]
    assert model.calls == []


def test_juan_in_portuguese_gets_a_portuguese_certificate(url: str, pool: ConnectionPool) -> None:
    start(pool, JUAN, locale="pt")
    run_until_idle(pool, scripted())
    assert cases(url, JUAN) == [("ended", "prequalified", "credit_card", "pt")]
    assert thread(url, JUAN) == [("template", certificate_for_policy("PREQUALIFIED", "pt", "credit_card"))]


def test_juliana_is_asked_for_her_income_and_decided_with_it(url: str, pool: ConnectionPool) -> None:
    started(pool, JULIANA)
    converse(url, pool, JULIANA, scripted("es-gano-45000-pesos"), INCOME)
    assert names(url, JULIANA) == [*NOTICE, *ANSWER, "analysis.completed", *POLICY_END]
    income_turn = payloads(url, JULIANA, "conversation.turn_classified")[-1]
    assert (income_turn["intent"], income_turn["product"], income_turn["income_requested"]) == (
        "provide_income",
        "credit_card",
        True,
    )
    asked, decided = payloads(url, JULIANA, "analysis.completed")
    assert (asked["outcome"], decided["outcome"]) == ("NEEDS_INFO", "PREQUALIFIED")
    assert decided["facts"] == facts(714, Decimal(45000), "MXN", None, "self_declared")
    assert [row[1] for row in queue(url)][-4:] == [
        "generate_while_ai",
        "run_policy_income",
        "render_decision",
        "end_after_decision",
    ]
    assert thread(url, JULIANA)[0] == ("template", render_notice("needs_income", "es", "credit_card"))
    assert cases(url, JULIANA) == [("ended", "prequalified", "credit_card", "es")]


def test_an_income_in_another_countrys_currency_is_asked_for_again(url: str, pool: ConnectionPool) -> None:
    colombian = ShownReading(TurnReading("provide_income", None, "es", Decimal(45000), "COP", "Gracias."))
    started(pool, JULIANA)
    converse(url, pool, JULIANA, ScriptedModel({COLOMBIAN_INCOME: colombian}), COLOMBIAN_INCOME)
    first, second = payloads(url, JULIANA, "analysis.completed")
    assert (first["outcome"], second["outcome"]) == ("NEEDS_INFO", "NEEDS_INFO")
    assert second["rule_trace"][-1] == {
        "rule_id": "R06",
        "input": {"income_local": None, "declared_income": None, "income_currency": "MXN"},
        "result": "NEEDS_INFO",
    }
    assert [p["template_id"] for p in payloads(url, JULIANA, "conversation.template_sent")] == [
        "needs_income",
        "needs_income",
    ]
    assert cases(url, JULIANA) == [("ai_active", None, "credit_card", "es")]


def test_alicia_is_referred_waits_for_a_person_and_is_closed_by_one(url: str, pool: ConnectionPool) -> None:
    model = scripted()
    started(pool, ALICIA)
    assert names(url, ALICIA) == [*NOTICE, *HANDOFF]
    assert cases(url, ALICIA) == [("human_active", None, "credit_card", "es")]
    assert payloads(url, ALICIA, "conversation.thread_taken") == [
        {"reason_code": "policy_refer", "from_state": "ai_active", "to_state": "human_active"}
    ]

    say(url, pool, ALICIA, "¿ya revisaron mi caso?")
    assert run_until_idle(pool, model) == []
    assert model.calls == []

    append(pool, consultant_closed(open_case_of(url, ALICIA), "PREQUALIFIED", CESAR, "es"))
    run_until_idle(pool, model)
    assert names(url, ALICIA)[-5:] == ["conversation.message_received", "conversation.consultant_closed", *POLICY_END]
    assert cases(url, ALICIA) == [("ended", "prequalified", "credit_card", "es")]
    assert thread(url, ALICIA) == [
        ("template", render_notice("refer_notice", "es", "credit_card")),
        ("template", certificate_for_close("PREQUALIFIED", "es", "credit_card")),
    ]
    assert payloads(url, ALICIA, "prequalification.decided")[0]["decided_by"] == "consultant"
    assert payloads(url, ALICIA, "process.ended") == [{"end_reason": "prequalified", "policy_version": None}]


def test_mariana_is_decided_by_delinquency(url: str, pool: ConnectionPool) -> None:
    started(pool, MARIANA, "personal_loan")
    [analysis] = payloads(url, MARIANA, "analysis.completed")
    assert (analysis["outcome"], analysis["deciding_rule"]) == ("NOT_PREQUALIFIED", "R02")
    assert cases(url, MARIANA) == [("ended", "not_prequalified", "personal_loan", "es")]
    assert thread(url, MARIANA)[-1] == ("template", certificate_for_policy("NOT_PREQUALIFIED", "es", "personal_loan"))


def test_mariana_asks_a_person_to_review_her_no_and_a_consultant_decides_it_again(
    url: str, pool: ConnectionPool
) -> None:
    started(pool, MARIANA)
    [(process_id,)] = query(url, "SELECT id FROM processes WHERE customer_id = %s", (MARIANA,))
    append(pool, appeal_requested(ProcessRow(process_id, MARIANA, "ended"), "es", "credit_card"))
    run_until_idle(pool, scripted())
    assert cases(url, MARIANA) == [("human_active", None, "credit_card", "es")]
    assert payloads(url, MARIANA, "conversation.thread_taken") == [
        {"reason_code": "customer_requested_human", "from_state": "ended", "to_state": "human_active"}
    ]

    append(pool, consultant_closed(open_case_of(url, MARIANA), "PREQUALIFIED", CESAR, "es"))
    run_until_idle(pool, scripted())
    assert cases(url, MARIANA) == [("ended", "prequalified", "credit_card", "es")]
    assert [p["decided_by"] for p in payloads(url, MARIANA, "prequalification.decided")] == ["policy", "consultant"]
    assert thread(url, MARIANA) == [
        ("template", certificate_for_policy("NOT_PREQUALIFIED", "es", "credit_card")),
        ("template", render_notice("refer_notice", "es", "credit_card")),
        ("template", certificate_for_close("PREQUALIFIED", "es", "credit_card")),
    ]
    assert [p["end_reason"] for p in payloads(url, MARIANA, "process.ended")] == ["not_prequalified", "prequalified"]


def test_a_question_about_the_products_is_answered_with_the_shown_reply(url: str, pool: ConnectionPool) -> None:
    fixture = load_turn_fixture("es-que-productos-ofrecen")
    started(pool, JULIANA)
    converse(url, pool, JULIANA, scripted("es-que-productos-ofrecen"), fixture.text)
    assert thread(url, JULIANA)[-1] == ("assistant", fixture.turn.reply_text)
    assert queue(url)[-1] == done("conversation.show_reply", "show_reply")
    assert cases(url, JULIANA) == [("ai_active", None, "credit_card", "es")]


def test_naming_a_product_with_its_own_open_case_points_to_that_case(url: str, pool: ConnectionPool) -> None:
    started(pool, JULIANA)
    started(pool, JULIANA, "personal_loan")
    [(card_id,)] = query(url, "SELECT id FROM processes WHERE customer_id = %s AND product = 'credit_card'", (JULIANA,))
    send(pool, JULIANA, LOAN, InCase(card_id))
    run_until_idle(pool, scripted("es-quiero-un-prestamo-personal"))
    turn = payloads(url, JULIANA, "conversation.turn_classified")[-1]
    assert (turn["product"], turn["open_case_product"]) == ("credit_card", "personal_loan")
    assert queue(url)[-1] == done("template.send", "point_to_open_case")
    notice = render_notice("product_case_open", "es", "personal_loan")
    assert query(url, "SELECT body FROM messages WHERE process_id = %s ORDER BY created_at", (card_id,))[-1] == (
        notice,
    )


def test_a_reply_that_states_an_outcome_is_withheld_and_sent_to_a_person(url: str, pool: ConnectionPool) -> None:
    states_outcome = WithheldReading(
        reading_of(load_turn_fixture("es-si-reply-states-outcome").turn), "reply_forbidden"
    )
    started(pool, JULIANA)
    converse(url, pool, JULIANA, ScriptedModel({"sí": states_outcome}), "sí")
    assert names(url, JULIANA) == [*NOTICE, *ANSWER, *HANDOFF]
    assert payloads(url, JULIANA, "conversation.thread_taken")[0]["reason_code"] == "reply_forbidden"
    assert [author for author, _ in thread(url, JULIANA)] == ["template"]


def test_three_model_failures_send_the_case_to_a_person(url: str, pool: ConnectionPool) -> None:
    started(pool, JULIANA)
    say(url, pool, JULIANA, INCOME)
    results = run_until_idle(pool, scripted("es-gano-45000-pesos", failures=3))
    assert results == [Retried(1, MODEL_DOWN), Retried(2, MODEL_DOWN), Failed(3, MODEL_DOWN)]
    assert queue(url)[-1] == ("conversation.generate", "generate_while_ai", "failed", 3, MODEL_DOWN)
    assert names(url, JULIANA) == [*NOTICE, "conversation.message_received", *HANDOFF]
    assert payloads(url, JULIANA, "conversation.thread_taken") == [
        {"reason_code": "tool_failed", "from_state": "ai_active", "to_state": "human_active"}
    ]
    assert cases(url, JULIANA) == [("human_active", None, "credit_card", "es")]


def test_a_failed_attempt_that_succeeds_next_writes_one_turn(url: str, pool: ConnectionPool) -> None:
    started(pool, JULIANA)
    converse(url, pool, JULIANA, scripted("es-gano-45000-pesos", failures=1), INCOME)
    assert names(url, JULIANA).count("conversation.turn_classified") == 1
    assert queue(url)[3] == ("conversation.generate", "generate_while_ai", "done", 2, MODEL_DOWN)


def test_without_a_model_adapter_the_command_fails_and_names_what_is_missing(url: str, pool: ConnectionPool) -> None:
    started(pool, JULIANA)
    say(url, pool, JULIANA, INCOME)
    run_until_idle(pool, model_not_built)
    name, _rule, status, attempts, error = queue(url)[-1]
    assert (name, status, attempts) == ("conversation.generate", "failed", 3)
    assert error == (
        "ModelNotBuilt: conversation.generate has no model adapter yet: M3 builds "
        "api/infrastructure/llm/conversation.py. Set LLM_MODEL=b0-keywords to read turns with the keyword baseline "
        "(PLAN.md D23)."
    )
    assert cases(url, JULIANA) == [("human_active", None, "credit_card", "es")]


def test_b0_reads_a_typed_message_when_llm_model_names_it(url: str, pool: ConnectionPool) -> None:
    started(pool, JULIANA)
    converse(url, pool, JULIANA, read_turn_for(B0_MODEL), INCOME)
    assert cases(url, JULIANA) == [("ended", "prequalified", "credit_card", "es")]


def test_llm_model_picks_what_reads_a_turn() -> None:
    assert read_turn_for(B0_MODEL) is read_keyword_turn
    assert read_turn_for("gpt-6-luna") is model_not_built
    with pytest.raises(ValueError, match="LLM_MODEL=gpt-4 names nothing that reads a turn"):
        read_turn_for("gpt-4")


def test_a_customer_with_no_credit_profile_fails_the_run_and_goes_to_a_person(url: str, pool: ConnectionPool) -> None:
    started(pool, NO_PROFILE)
    assert queue(url)[1] == (
        "policy.run",
        "run_requested_policy",
        "failed",
        3,
        f"MissingProfile: customer {NO_PROFILE} has no row in customer_credit_profile",
    )
    assert cases(url, NO_PROFILE) == [("human_active", None, "credit_card", "es")]


def test_a_message_delivered_twice_plans_nothing_new(url: str, pool: ConnectionPool) -> None:
    message_id = uuid4()
    start(pool, JUAN, message_id=message_id)
    run_until_idle(pool, scripted())
    before = queue(url)
    stamp = MessageStamp(None, "ai_active")
    again = append(pool, message_received(JUAN, OPENING["credit_card"], message_id, "es", "credit_card", stamp))
    assert isinstance(again, AlreadyAppended)
    assert run_until_idle(pool, scripted()) == []
    assert queue(url) == before


def test_a_message_that_reaches_a_case_handed_off_before_its_turn_does_not_call_the_model(
    url: str, pool: ConnectionPool
) -> None:
    model = scripted("es-quiero-hablar-con-una-persona")
    started(pool, JULIANA)
    say(url, pool, JULIANA, HUMAN)
    assert isinstance(run_next(pool, model), Done)
    say(url, pool, JULIANA, "sí")
    run_until_idle(pool, model)
    assert [request.text for request in model.calls] == [HUMAN]
    assert names(url, JULIANA) == [*NOTICE, *ANSWER, "conversation.message_received", *HANDOFF]
    assert queue(url)[-2:] == [
        done("process.transition", "hand_off_human"),
        done("conversation.generate", "generate_while_ai"),
    ]


def test_two_starts_for_one_product_before_the_case_opens_join_one_case(url: str, pool: ConnectionPool) -> None:
    start(pool, JUAN)
    start(pool, JUAN)
    run_until_idle(pool, scripted())
    assert cases(url, JUAN) == [("ended", "prequalified", "credit_card", "es")]
    assert names(url, JUAN).count("process.started") == 1
    assert names(url, JUAN).count("analysis.completed") == 1
    assert [row[1] for row in queue(url)].count("run_requested_policy") == 1


def test_one_customers_commands_wait_for_each_other_while_another_customer_goes_ahead(
    url: str, pool: ConnectionPool
) -> None:
    start(pool, JUAN)
    start(pool, ALICIA)
    with psycopg.connect(url) as first, psycopg.connect(url) as second, psycopg.connect(url) as third:
        for conn in (first, second, third):
            configure_json(conn)
        juan_start = PostgresCommands(first).claim_next()
        alicia_start = PostgresCommands(second).claim_next()
        assert PostgresCommands(third).claim_next() is None
    assert juan_start is not None
    assert alicia_start is not None
    owners = query(url, "SELECT id, customer_id FROM events WHERE event_name = 'conversation.message_received'")
    by_event = dict(owners)
    assert [by_event[juan_start.triggered_by_event_id], by_event[alicia_start.triggered_by_event_id]] == [JUAN, ALICIA]
    assert [juan_start.command.command_name, alicia_start.command.command_name] == ["process.start", "process.start"]


def test_a_handoff_that_is_not_an_appeal_cannot_reopen_an_ended_case(url: str, pool: ConnectionPool) -> None:
    started(pool, MARIANA)
    sql = "SELECT id FROM events WHERE customer_id = %s AND event_name = %s"
    [(analysis_id,)] = query(url, sql, (MARIANA, ANALYSIS_COMPLETED))
    move = hand_off(CUSTOMER_REQUESTED_HUMAN)
    with pool.connection() as conn:
        key = command_key("hand_off_human", move.command_name, analysis_id)
        PostgresCommands(conn).enqueue(PlannedCommand(move, "hand_off_human", analysis_id, key))
    run_until_idle(pool, scripted())
    assert queue(url)[-1][:4] == ("process.transition", "hand_off_human", "failed", 3)
    assert str(queue(url)[-1][4]).startswith("IllegalTransition: process cannot move from ended to human_active")
    assert cases(url, MARIANA) == [("ended", "not_prequalified", "credit_card", "es")]


def test_a_command_with_no_case_to_hand_off_fails_without_a_handoff(url: str, pool: ConnectionPool) -> None:
    with pool.connection() as conn:
        message = PostgresEvents(conn).append(
            message_received(JUAN, CARD, uuid4(), "es", None, MessageStamp(None, "ai_active"))
        )
        key = command_key("generate_while_ai", "conversation.generate", message.event_id)
        PostgresCommands(conn).enqueue(PlannedCommand(GENERATE_COMMAND, "generate_while_ai", message.event_id, key))
    run_until_idle(pool, scripted("es-quiero-una-tarjeta-de-credito"))
    assert queue(url)[0][2:4] == ("failed", 3)
    assert names(url, JUAN) == ["conversation.message_received"]


# A case from before D24 has no product, so the consultant's certificate cannot name one.
def test_a_certificate_that_cannot_be_written_stops_the_close_before_the_case_ends(
    url: str, pool: ConnectionPool
) -> None:
    started(pool, JULIANA)
    converse(url, pool, JULIANA, scripted("es-quiero-hablar-con-una-persona"), HUMAN)
    with psycopg.connect(url) as conn:
        conn.execute("UPDATE processes SET product = NULL WHERE customer_id = %s", (JULIANA,))
    append(pool, consultant_closed(open_case_of(url, JULIANA), "NOT_PREQUALIFIED", CESAR, "es"))
    run_until_idle(pool, scripted())
    render, end = queue(url)[-2:]
    assert render == (
        "decision.render",
        "close_on_consultant_decision",
        "failed",
        3,
        "MissingProduct: the consultant certificate names the product, and none was given",
    )
    assert end[:4] == ("process.end", "close_on_consultant_decision", "failed", 0)
    assert str(end[4]).startswith("an earlier command of the same event failed: ")
    assert cases(url, JULIANA) == [("human_active", None, None, "es")]
    assert "prequalification.decided" not in names(url, JULIANA)


def test_the_worker_thread_runs_a_cycle_and_the_handler_can_wait_for_it(url: str, pool: ConnectionPool) -> None:
    worker = Worker(pool, scripted(), poll_seconds=0.05)
    message = start(pool, JUAN)
    assert worker.wait_for_cycle(message, 0.05) is False
    worker.start()
    worker.wake()
    try:
        assert worker.wait_for_cycle(message, 10) is True
    finally:
        worker.stop()
    assert names(url, JUAN) == [*START, *POLICY_END]


def test_the_worker_keeps_polling_after_it_cannot_take_a_command(
    url: str, pool: ConnectionPool, monkeypatch: pytest.MonkeyPatch
) -> None:
    lost: list[bool] = []

    def flaky(*args: Any) -> Any:
        if not lost:
            lost.append(True)
            raise psycopg.OperationalError("connection lost")
        return run_next(*args)

    monkeypatch.setattr(loop, "run_next", flaky)
    worker = Worker(pool, scripted(), poll_seconds=0.05)
    message = start(pool, JUAN)
    worker.start()
    try:
        assert worker.wait_for_cycle(message, 10) is True
    finally:
        worker.stop()
    assert lost == [True]


def test_the_api_runs_the_worker_only_when_asked(url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "database_url", url)
    monkeypatch.setattr(settings, "run_worker", True)
    with TestClient(app):
        assert isinstance(app.state.worker, Worker)
    monkeypatch.setattr(settings, "run_worker", False)
    with TestClient(app):
        assert app.state.worker is None


def test_the_repositories_name_what_does_not_exist(url: str, pool: ConnectionPool) -> None:
    missing = uuid4()
    with pool.connection() as conn:
        log, processes = PostgresEventLog(conn), PostgresProcesses(conn)
        with pytest.raises(LookupError, match=f"event {missing} does not exist"):
            log.read(missing)
        with pytest.raises(LookupError, match=f"process {missing} does not exist"):
            processes.product_of(missing)
        assert processes.read(missing) is None
        assert PostgresProfiles(conn).read(NO_PROFILE) is None
