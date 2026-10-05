import time
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest

from api.application.processes import (
    AlreadyApplied,
    AlreadyOpen,
    AlreadyStarted,
    Applied,
    CaseAlreadyOpen,
    CaseEnded,
    CaseNotFound,
    InCase,
    MessageTarget,
    ProcessNotFound,
    StartCase,
    Started,
    end_process,
    hand_off_process,
    record_customer_message,
    start_process,
)
from api.contract_models import Locale
from api.domain.process.lifecycle import IllegalTransition
from api.domain.process.new_events import (
    AlreadyAppended,
    Appended,
    Cause,
    IdempotencyConflict,
    NewEvent,
)
from api.infrastructure.db.events import PostgresEvents
from api.infrastructure.db.processes import PostgresProcesses

pytestmark = pytest.mark.integration

CYCLE_TEST_DB = "alba_process_cycle_test"
JUAN = "CLI-9EDEKZ8OUNUR"
ALICIA = "CLI-440CO5FZIY6A"
type Work[Result] = Callable[[PostgresEvents, PostgresProcesses], Result]


@pytest.fixture(scope="module")
def cycle_database(migrated_database: Callable[[str], str]) -> str:
    return migrated_database(CYCLE_TEST_DB)


@pytest.fixture
def url(cycle_database: str) -> Iterator[str]:
    with psycopg.connect(cycle_database) as conn:
        conn.execute("TRUNCATE events, messages, processes")
    yield cycle_database


def run[Result](url: str, work: Work[Result]) -> Result:
    with psycopg.connect(url) as conn:
        return work(PostgresEvents(conn), PostgresProcesses(conn))


CARD = StartCase("credit_card")


def send(
    url: str,
    customer_id: str,
    text: str,
    client_message_id: UUID | None = None,
    locale: Locale = "es",
    target: MessageTarget = CARD,
) -> UUID:
    message_id = client_message_id or uuid4()
    result = run(url, lambda e, p: record_customer_message(e, p, customer_id, text, message_id, locale, target))
    assert isinstance(result, Appended)
    return result.event_id


def open_case(url: str, customer_id: str) -> tuple[UUID, UUID]:
    message = send(url, customer_id, "quiero una tarjeta de crédito")
    started = run(url, lambda e, p: start_process(e, p, customer_id, "es", "credit_card", Cause(message, None)))
    assert isinstance(started, Started)
    return message, started.process_id


# Rows come back as plain tuples so each assertion compares the whole stored fact.
def events(url: str) -> list[tuple[Any, ...]]:
    with psycopg.connect(url) as conn:
        return conn.execute(
            """
            SELECT event_name, idempotency_key, actor, customer_id, process_id, process_state,
                   caused_by_event_id, caused_by_command_id, payload
            FROM events ORDER BY seq
            """
        ).fetchall()


def processes(url: str) -> list[tuple[Any, ...]]:
    with psycopg.connect(url) as conn:
        return conn.execute(
            "SELECT id, customer_id, process_key, state, end_reason, product, locale FROM processes ORDER BY created_at, id"
        ).fetchall()


def wait_until_blocked(url: str, backend_pid: int) -> None:
    deadline = time.monotonic() + 5
    with psycopg.connect(url, autocommit=True) as watcher:
        while time.monotonic() < deadline:
            row = watcher.execute(
                "SELECT wait_event_type FROM pg_stat_activity WHERE pid = %s", (backend_pid,)
            ).fetchone()
            if row is not None and row[0] == "Lock":
                return
            time.sleep(0.01)
    raise AssertionError(f"backend {backend_pid} never waited on a lock")


def test_a_first_message_has_no_process_and_is_born_ai_active(url: str) -> None:
    client_message_id = uuid4()
    message = send(url, JUAN, "quiero una tarjeta de crédito", client_message_id)
    assert [row[1:] for row in events(url)] == [
        (
            f"msg:{client_message_id}",
            "customer",
            JUAN,
            None,
            "ai_active",
            None,
            None,
            {
                "text": "quiero una tarjeta de crédito",
                "client_message_id": str(client_message_id),
                "locale": "es",
                "product": "credit_card",
            },
        )
    ]
    assert events(url)[0][0] == "conversation.message_received"
    assert processes(url) == []
    assert isinstance(message, UUID)


def test_the_same_send_twice_writes_one_event(url: str) -> None:
    client_message_id = uuid4()
    first = send(url, JUAN, "sí", client_message_id)
    again = run(url, lambda e, p: record_customer_message(e, p, JUAN, "sí", client_message_id, "es", CARD))
    assert again == AlreadyAppended(first)
    assert len(events(url)) == 1


@pytest.mark.parametrize(
    ("customer_id", "text", "locale"),
    [(JUAN, "no", "es"), (ALICIA, "sí", "es"), (JUAN, "sí", "pt")],
    ids=["other text", "other customer", "other language"],
)
def test_a_reused_message_id_for_another_fact_is_refused(url: str, customer_id: str, text: str, locale: Locale) -> None:
    client_message_id = uuid4()
    send(url, JUAN, "sí", client_message_id)
    with pytest.raises(IdempotencyConflict, match=f"msg:{client_message_id}"):
        run(url, lambda e, p: record_customer_message(e, p, customer_id, text, client_message_id, locale, CARD))
    assert len(events(url)) == 1


def test_a_key_reused_by_another_event_name_is_refused(url: str) -> None:
    client_message_id = uuid4()
    send(url, JUAN, "sí", client_message_id)
    impostor = NewEvent(
        event_name="process.started",
        idempotency_key=f"msg:{client_message_id}",
        customer_id=JUAN,
        process_id=None,
        process_state="ai_active",
        caused_by_event_id=None,
        caused_by_command_id=None,
        payload={"text": "sí", "client_message_id": str(client_message_id)},
    )
    with pytest.raises(IdempotencyConflict):
        run(url, lambda e, _: e.append(impostor))
    assert len(events(url)) == 1


def test_start_opens_the_case_and_points_at_its_message(url: str) -> None:
    command_id = uuid4()
    message = send(url, JUAN, "quiero una tarjeta de crédito")
    started = run(url, lambda e, p: start_process(e, p, JUAN, "es", "credit_card", Cause(message, command_id)))
    assert isinstance(started, Started)
    assert processes(url) == [
        (started.process_id, JUAN, "credit_prequalification", "ai_active", None, "credit_card", "es")
    ]
    assert events(url)[1] == (
        "process.started",
        f"process:{JUAN}:credit_prequalification:{message}",
        "system",
        JUAN,
        started.process_id,
        "ai_active",
        message,
        command_id,
        {"process_key": "credit_prequalification", "customer_id": JUAN, "locale": "es", "product": "credit_card"},
    )


def test_a_case_keeps_the_language_of_its_opening_message(url: str) -> None:
    message = send(url, JUAN, "quero um cartão de crédito", locale="pt")
    started = run(url, lambda e, p: start_process(e, p, JUAN, "pt", "credit_card", Cause(message, None)))
    assert isinstance(started, Started)
    assert [row[6] for row in processes(url)] == ["pt"]
    assert events(url)[0][8]["locale"] == "pt"
    assert events(url)[1][8]["locale"] == "pt"


def test_a_message_joins_the_open_case_with_its_state(url: str) -> None:
    message, process_id = open_case(url, JUAN)
    send(url, JUAN, "¿qué tasa tiene?", target=InCase(process_id))
    run(url, lambda e, p: hand_off_process(e, p, process_id, "customer_requested_human", Cause(message, None)))
    send(url, JUAN, "¿hay alguien?", target=InCase(process_id))
    stamps = [(row[0], row[4], row[5]) for row in events(url) if row[0] == "conversation.message_received"]
    assert stamps == [
        ("conversation.message_received", None, "ai_active"),
        ("conversation.message_received", process_id, "ai_active"),
        ("conversation.message_received", process_id, "human_active"),
    ]


def test_another_customers_open_case_is_not_stamped_on_this_message(url: str) -> None:
    open_case(url, ALICIA)
    send(url, JUAN, "hola")
    assert [row[3:6] for row in events(url)][-1] == (JUAN, None, "ai_active")


def test_a_message_after_an_ended_case_opens_a_new_case(url: str) -> None:
    message, first = open_case(url, JUAN)
    run(url, lambda e, p: end_process(e, p, first, "prequalified", "alba-credit-v1", Cause(message, None)))
    later = send(url, JUAN, "quiero un préstamo personal")
    assert [row[4:6] for row in events(url)][-1] == (None, "ai_active")
    second = run(url, lambda e, p: start_process(e, p, JUAN, "es", "credit_card", Cause(later, None)))
    assert isinstance(second, Started)
    assert [(row[0], row[3], row[4]) for row in processes(url)] == [
        (first, "ended", "prequalified"),
        (second.process_id, "ai_active", None),
    ]


def test_a_replayed_start_returns_its_case_even_after_it_ended(url: str) -> None:
    message, process_id = open_case(url, JUAN)
    run(url, lambda e, p: end_process(e, p, process_id, "not_prequalified", "alba-credit-v1", Cause(message, None)))
    before = events(url)
    replay = run(url, lambda e, p: start_process(e, p, JUAN, "es", "credit_card", Cause(message, None)))
    assert replay == AlreadyStarted(process_id)
    assert events(url) == before
    assert len(processes(url)) == 1


def test_a_second_start_sent_before_the_case_opens_joins_it(url: str) -> None:
    first_message = send(url, JUAN, "quiero una tarjeta de crédito")
    second_message = send(url, JUAN, "quiero una tarjeta de crédito")
    first = run(url, lambda e, p: start_process(e, p, JUAN, "es", "credit_card", Cause(first_message, None)))
    joined = run(url, lambda e, p: start_process(e, p, JUAN, "es", "credit_card", Cause(second_message, None)))
    assert isinstance(first, Started)
    assert joined == AlreadyOpen(first.process_id)
    assert [row[0] for row in events(url)] == [
        "conversation.message_received",
        "conversation.message_received",
        "process.started",
    ]
    assert len(processes(url)) == 1


def test_a_start_for_a_product_with_an_open_case_is_refused(url: str) -> None:
    open_case(url, JUAN)
    with pytest.raises(CaseAlreadyOpen, match="credit_card"):
        send(url, JUAN, "quiero una tarjeta de crédito")


def test_each_product_has_its_own_open_case(url: str) -> None:
    open_case(url, JUAN)
    loan = send(url, JUAN, "quiero un préstamo personal", target=StartCase("personal_loan"))
    second = run(url, lambda e, p: start_process(e, p, JUAN, "es", "personal_loan", Cause(loan, None)))
    assert isinstance(second, Started)
    assert sorted(row[5] for row in processes(url)) == ["credit_card", "personal_loan"]


def test_a_message_to_another_customers_case_is_refused(url: str) -> None:
    _, alicias = open_case(url, ALICIA)
    with pytest.raises(CaseNotFound):
        send(url, JUAN, "hola", target=InCase(alicias))


def test_a_message_to_an_ended_case_is_refused_but_its_replay_is_not(url: str) -> None:
    message, process_id = open_case(url, JUAN)
    client_message_id = uuid4()
    send(url, JUAN, "gracias", client_message_id, target=InCase(process_id))
    run(url, lambda e, p: end_process(e, p, process_id, "prequalified", "alba-credit-v1", Cause(message, None)))
    with pytest.raises(CaseEnded):
        send(url, JUAN, "una pregunta más", target=InCase(process_id))
    replay = run(
        url,
        lambda e, p: record_customer_message(e, p, JUAN, "gracias", client_message_id, "es", InCase(process_id)),
    )
    assert isinstance(replay, AlreadyAppended)


def test_two_starts_at_once_open_one_case(url: str) -> None:
    first_message = send(url, JUAN, "quiero una tarjeta")
    second_message = send(url, JUAN, "quiero un préstamo")
    with psycopg.connect(url) as holder, psycopg.connect(url) as waiter, ThreadPoolExecutor(1) as pool:
        first = start_process(
            PostgresEvents(holder), PostgresProcesses(holder), JUAN, "es", "credit_card", Cause(first_message, None)
        )
        second = pool.submit(
            start_process,
            PostgresEvents(waiter),
            PostgresProcesses(waiter),
            JUAN,
            "es",
            "credit_card",
            Cause(second_message, None),
        )
        wait_until_blocked(url, waiter.info.backend_pid)
        holder.commit()
        assert isinstance(first, Started)
        assert second.result(timeout=5) == AlreadyOpen(first.process_id)
    assert len(processes(url)) == 1
    assert [row[0] for row in events(url)].count("process.started") == 1


def test_a_message_sent_during_a_handoff_carries_the_handoffs_result(url: str) -> None:
    message, process_id = open_case(url, JUAN)
    with psycopg.connect(url) as holder, psycopg.connect(url) as waiter, ThreadPoolExecutor(1) as pool:
        hand_off_process(
            PostgresEvents(holder), PostgresProcesses(holder), process_id, "out_of_scope", Cause(message, None)
        )
        sent = pool.submit(
            record_customer_message,
            PostgresEvents(waiter),
            PostgresProcesses(waiter),
            JUAN,
            "¿sigue ahí?",
            uuid4(),
            "es",
            InCase(process_id),
        )
        wait_until_blocked(url, waiter.info.backend_pid)
        holder.commit()
        assert isinstance(sent.result(timeout=5), Appended)
    assert [row[4:6] for row in events(url)][-1] == (process_id, "human_active")


def test_a_handoff_writes_state_changed_then_thread_taken(url: str) -> None:
    message, process_id = open_case(url, JUAN)
    command_id = uuid4()
    moved = run(url, lambda e, p: hand_off_process(e, p, process_id, "policy_refer", Cause(message, command_id)))
    action = f"transition:{process_id}:human_active:{message}"
    assert moved == Applied(process_id)
    assert events(url)[2:] == [
        (
            "process.state_changed",
            f"{action}:process.state_changed",
            "system",
            JUAN,
            process_id,
            "human_active",
            message,
            command_id,
            {"from_state": "ai_active", "to_state": "human_active", "end_reason": None},
        ),
        (
            "conversation.thread_taken",
            f"{action}:conversation.thread_taken",
            "system",
            JUAN,
            process_id,
            "human_active",
            message,
            command_id,
            {"reason_code": "policy_refer", "from_state": "ai_active", "to_state": "human_active"},
        ),
    ]
    assert [row[3:5] for row in processes(url)] == [("human_active", None)]


def test_a_replayed_handoff_writes_nothing_even_after_the_case_ended(url: str) -> None:
    message, process_id = open_case(url, JUAN)
    run(url, lambda e, p: hand_off_process(e, p, process_id, "policy_refer", Cause(message, None)))
    run(url, lambda e, p: end_process(e, p, process_id, "prequalified", None, Cause(message, None)))
    before = events(url)
    replay = run(url, lambda e, p: hand_off_process(e, p, process_id, "policy_refer", Cause(message, None)))
    assert replay == AlreadyApplied(process_id)
    assert events(url) == before


@pytest.mark.parametrize("handed_off", [False, True], ids=["from ai_active", "from human_active"])
def test_an_end_writes_both_events_with_one_end_reason(url: str, handed_off: bool) -> None:
    message, process_id = open_case(url, JUAN)
    if handed_off:
        run(url, lambda e, p: hand_off_process(e, p, process_id, "policy_refer", Cause(message, None)))
    from_state = "human_active" if handed_off else "ai_active"
    ended = run(url, lambda e, p: end_process(e, p, process_id, "prequalified", "alba-credit-v1", Cause(message, None)))
    assert ended == Applied(process_id)
    assert events(url)[-2:] == [
        (
            "process.state_changed",
            f"end:{process_id}:{message}:process.state_changed",
            "system",
            JUAN,
            process_id,
            "ended",
            message,
            None,
            {"from_state": from_state, "to_state": "ended", "end_reason": "prequalified"},
        ),
        (
            "process.ended",
            f"end:{process_id}:{message}:process.ended",
            "system",
            JUAN,
            process_id,
            "ended",
            message,
            None,
            {"end_reason": "prequalified", "policy_version": "alba-credit-v1"},
        ),
    ]
    assert [row[3:5] for row in processes(url)] == [("ended", "prequalified")]


def test_a_replayed_end_writes_nothing(url: str) -> None:
    message, process_id = open_case(url, JUAN)
    run(url, lambda e, p: end_process(e, p, process_id, "prequalified", "alba-credit-v1", Cause(message, None)))
    before = events(url)
    replay = run(
        url, lambda e, p: end_process(e, p, process_id, "prequalified", "alba-credit-v1", Cause(message, None))
    )
    assert replay == AlreadyApplied(process_id)
    assert events(url) == before


def test_an_illegal_handoff_raises_and_writes_nothing(url: str) -> None:
    message, process_id = open_case(url, JUAN)
    run(url, lambda e, p: hand_off_process(e, p, process_id, "policy_refer", Cause(message, None)))
    before_events, before_processes = events(url), processes(url)
    later = send(url, JUAN, "quiero un préstamo personal", target=StartCase("personal_loan"))
    with pytest.raises(IllegalTransition):
        run(url, lambda e, p: hand_off_process(e, p, process_id, "out_of_scope", Cause(later, None)))
    assert [row for row in events(url) if row[0] != "conversation.message_received"] == [
        row for row in before_events if row[0] != "conversation.message_received"
    ]
    assert processes(url) == before_processes


def test_moving_a_process_that_does_not_exist_fails_loud(url: str) -> None:
    missing = uuid4()
    with pytest.raises(ProcessNotFound, match=str(missing)):
        run(url, lambda e, p: hand_off_process(e, p, missing, "policy_refer", Cause(uuid4(), None)))
    with pytest.raises(ProcessNotFound, match=str(missing)):
        run(url, lambda e, p: end_process(e, p, missing, "prequalified", None, Cause(uuid4(), None)))
    assert events(url) == []


def test_an_ended_case_reopens_for_a_person_and_ends_again(url: str) -> None:
    message, process_id = open_case(url, JUAN)
    run(url, lambda e, p: end_process(e, p, process_id, "not_prequalified", "alba-credit-v1", Cause(message, None)))
    appeal = send(url, JUAN, "quiero un préstamo personal", target=StartCase("personal_loan"))
    reopened = run(
        url, lambda e, p: hand_off_process(e, p, process_id, "customer_requested_human", Cause(appeal, None))
    )
    assert reopened == Applied(process_id)
    assert [row[3] for row in processes(url) if row[0] == process_id] == ["human_active"]
    ended = run(url, lambda e, p: end_process(e, p, process_id, "prequalified", None, Cause(appeal, None)))
    assert ended == Applied(process_id)
    assert [(row[3], row[4]) for row in processes(url) if row[0] == process_id] == [("ended", "prequalified")]
