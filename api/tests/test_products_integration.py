from datetime import UTC, datetime

import psycopg
import pytest

from api.contract_models import Role
from api.domain.session.tokens import SessionClaims, issue_token
from api.infrastructure.config.settings import settings
from api.tests.login_harness import ALICIA, CESAR, GONZALEZ, JUAN, JULIANA, Harness

pytestmark = pytest.mark.integration

JUAN_SAVINGS = {
    "product_id": "PRD-AQZ0094E1XY0",
    "product_type": "Cuenta Ahorro",
    "product_number": "8482915725",
    "currency": "USD",
    "current_balance": 1559.57,
    "product_status": "Active",
}
JUAN_MORTGAGE = {
    "product_id": "PRD-W1ZJKF7U5B6C",
    "product_type": "Préstamo Hipotecario",
    "product_number": "LOAN-31561597",
    "currency": "USD",
    "current_balance": 109159.57,
    "product_status": "Active",
}
JULIANA_CHECKING = {
    "product_id": "PRD-73YY3EIYFXIK",
    "product_type": "Cuenta Corriente",
    "product_number": "2160977377",
    "currency": "USD",
    "current_balance": 2528.58,
    "product_status": "Active",
}
ALICIA_CHECKING = {
    "product_id": "PRD-HSUB9M7052JT",
    "product_type": "Cuenta Corriente",
    "product_number": "5964932955",
    "currency": "COP",
    "current_balance": 13192324.57,
    "product_status": "Active",
}
ALICIA_INSURANCE = {
    "product_id": "PRD-LAS2SGNHG44Y",
    "product_type": "Seguro",
    "product_number": "POL-6911709",
    "currency": "USD",
    "current_balance": 0.0,
    "product_status": "Active",
}
ALICIA_CLOSED_SAVINGS = {
    "product_id": "PRD-YT0DEZDUN1I4",
    "product_type": "Cuenta Ahorro",
    "product_number": "2079790665",
    "currency": "COP",
    "current_balance": 1419507.66,
    "product_status": "Closed",
}
PAID_PERSONAL_LOAN = {
    "product_id": "PRD-TESTLOAN0001",
    "product_type": "Préstamo Personal",
    "product_number": "LOAN-20000001",
    "currency": "MXN",
    "current_balance": 0.0,
    "product_status": "Active",
}
CREDIT_CARD_AT_ZERO = {
    "product_id": "PRD-TESTCARD0001",
    "product_type": "Tarjeta Crédito",
    "product_number": "4111111111115476",
    "currency": "USD",
    "current_balance": 0.0,
    "product_status": "Active",
}
DAYS_PAST_DUE = {JUAN_MORTGAGE["product_id"]: 0}
WITHOUT_PRODUCTS = GONZALEZ[0]
WITH_A_PAID_LOAN = GONZALEZ[1]
SEEDED = [
    (JUAN.customer_id, JUAN_MORTGAGE),
    (ALICIA.customer_id, ALICIA_CLOSED_SAVINGS),
    (JUAN.customer_id, JUAN_SAVINGS),
    (JULIANA.customer_id, JULIANA_CHECKING),
    (ALICIA.customer_id, ALICIA_INSURANCE),
    (ALICIA.customer_id, ALICIA_CHECKING),
    (WITH_A_PAID_LOAN.customer_id, PAID_PERSONAL_LOAN),
    (WITH_A_PAID_LOAN.customer_id, CREDIT_CARD_AT_ZERO),
]


@pytest.fixture(scope="module", autouse=True)
def seeded_products(login_database: str) -> None:
    with psycopg.connect(login_database) as conn:
        conn.cursor().executemany(
            """
            INSERT INTO products
                (product_id, customer_id, product_type, product_number, currency, current_balance, product_status, days_past_due)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [
                (
                    product["product_id"],
                    customer_id,
                    product["product_type"],
                    product["product_number"],
                    product["currency"],
                    str(product["current_balance"]),
                    product["product_status"],
                    DAYS_PAST_DUE.get(str(product["product_id"])),
                )
                for customer_id, product in SEEDED
            ],
        )


def bearer(sub: str, role: Role = "customer") -> dict[str, str]:
    token = issue_token(settings.jwt_secret, SessionClaims(sub=sub, role=role), datetime.now(UTC))
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("params", [{}, {"customer_id": JUAN.customer_id}])
def test_juan_sees_his_own_products_in_product_id_order(harness: Harness, params: dict[str, str]) -> None:
    response = harness.http.get("/products", params=params, headers=bearer(JUAN.customer_id))
    assert response.status_code == 200
    assert response.json() == {"products": [JUAN_SAVINGS, JUAN_MORTGAGE]}


def test_balances_of_customers_in_mexico_stay_in_usd(harness: Harness) -> None:
    response = harness.http.get("/products", headers=bearer(JULIANA.customer_id))
    assert response.json() == {"products": [JULIANA_CHECKING]}


def test_balances_show_the_currency_stored_on_each_product_and_closed_products_are_left_out(harness: Harness) -> None:
    response = harness.http.get("/products", headers=bearer(ALICIA.customer_id))
    assert response.json() == {"products": [ALICIA_CHECKING, ALICIA_INSURANCE]}


def test_a_loan_at_zero_is_left_out_and_a_card_at_zero_is_not(harness: Harness) -> None:
    response = harness.http.get("/products", headers=bearer(WITH_A_PAID_LOAN.customer_id))
    assert response.json() == {"products": [CREDIT_CARD_AT_ZERO]}


def test_a_customer_cannot_see_another_customers_products(harness: Harness) -> None:
    response = harness.http.get(
        "/products", params={"customer_id": ALICIA.customer_id}, headers=bearer(JUAN.customer_id)
    )
    assert response.status_code == 200
    assert response.json() == {"products": []}


def test_a_customer_without_products_gets_an_empty_list(harness: Harness) -> None:
    response = harness.http.get("/products", headers=bearer(WITHOUT_PRODUCTS.customer_id))
    assert response.status_code == 200
    assert response.json() == {"products": []}


def test_an_empty_customer_id_is_an_invalid_request(harness: Harness) -> None:
    response = harness.http.get("/products", params={"customer_id": ""}, headers=bearer(JUAN.customer_id))
    assert response.status_code == 422
    assert response.json() == {"error": "invalid_body"}


def test_a_consultant_token_cannot_read_products(harness: Harness) -> None:
    response = harness.http.get("/products", headers=bearer(CESAR.consultant_id, "consultant"))
    assert response.status_code == 403
    assert response.json() == {"error": "forbidden"}


def test_products_without_a_token_is_401(harness: Harness) -> None:
    response = harness.http.get("/products")
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}
