from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import psycopg
from fastapi.testclient import TestClient

from api.contract_models import Locale, ProductKey, Role
from api.domain.policy.templates import render_notice
from api.domain.session.tokens import SessionClaims, issue_token
from api.infrastructure.config.settings import settings
from api.tests.cycle_harness import MARIANA
from api.tests.login_harness import JUAN
from api.tests.oracle import oracle_customer, seed_oracle_profiles

CHAT_TEST_DB = "alba_chat_test"
AS_OF = "2026-06-17"
CARD_ES = "Quiero una tarjeta de crédito"
NEEDS_INCOME_ES = render_notice("needs_income", "es", "credit_card")
REFER_NOTICE_ES = render_notice("refer_notice", "es", "credit_card")
CESAR = "AGT-OJ9N4FGYV9"


def seed_profiles(url: str) -> None:
    mariana = oracle_customer(MARIANA)
    with psycopg.connect(url) as conn:
        conn.execute(
            """
            INSERT INTO customers (customer_id, document_number, first_name, last_name, email, country, segment,
                                   customer_status)
            VALUES (%s, '0000009643', %s, %s, NULL, %s, %s, %s)
            """,
            (MARIANA, mariana.first_name, mariana.last_name, mariana.country, mariana.segment, mariana.customer_status),
        )
        seed_oracle_profiles(conn)


def reset(url: str) -> None:
    with psycopg.connect(url) as conn:
        conn.execute("TRUNCATE commands, messages, events, processes")


def bearer(sub: str, role: Role = "customer") -> dict[str, str]:
    token = issue_token(settings.jwt_secret, SessionClaims(sub=sub, role=role), datetime.now(UTC))
    return {"Authorization": f"Bearer {token}"}


def post(http: TestClient, body: dict[str, Any], sub: str) -> dict[str, Any]:
    response = http.post("/messages", json=body, headers=bearer(sub))
    assert response.status_code == 200, response.text
    case = response.json()
    assert isinstance(case, dict)
    return case


def start_body(product: ProductKey, locale: Locale, text: str, message_id: UUID | None) -> dict[str, str]:
    return {"text": text, "client_message_id": str(message_id or uuid4()), "locale": locale, "product": product}


def start(
    http: TestClient,
    product: ProductKey = "credit_card",
    sub: str = JUAN.customer_id,
    locale: Locale = "es",
    text: str = CARD_ES,
    message_id: UUID | None = None,
) -> dict[str, Any]:
    return post(http, start_body(product, locale, text, message_id), sub)


def say(http: TestClient, case: dict[str, Any], text: str, sub: str, locale: Locale = "es") -> dict[str, Any]:
    body = {"text": text, "client_message_id": str(uuid4()), "locale": locale, "process_id": case["process_id"]}
    return post(http, body, sub)


def appeal(http: TestClient, case: dict[str, Any], sub: str) -> Any:
    return http.post(f"/case/{case['process_id']}/appeal", json={"locale": "es"}, headers=bearer(sub))


def lines(case: dict[str, Any]) -> list[tuple[str, str]]:
    return [(message["author"], message["body"]) for message in case["messages"]]


# Every field of the case but its ids, so a field that changes or appears turns the test red.
def shape(case: dict[str, Any]) -> tuple[Any, ...]:
    return (case["state"], case["end_reason"], case["product"], case["locale"], case["appealable"], lines(case))


def commands(url: str) -> list[tuple[str, str, int]]:
    with psycopg.connect(url) as conn:
        rows = conn.execute("SELECT command_name, status, attempt_count FROM commands ORDER BY seq").fetchall()
    return [(name, status, attempts) for name, status, attempts in rows]


def certificate(case: dict[str, Any], **fields: Any) -> dict[str, Any]:
    return {"event_id": case["messages"][-1]["event_id"], **fields}


def close(http: TestClient, case: dict[str, Any], outcome: str, sub: str = CESAR, role: Role = "consultant") -> Any:
    return http.post(
        f"/consultant/case/{case['process_id']}/close", json={"outcome": outcome}, headers=bearer(sub, role)
    )
