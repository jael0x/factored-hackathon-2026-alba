import os
from collections.abc import Iterator
from typing import get_args

import psycopg
import pytest

from api.contract_models import ProductKey
from api.domain.policy.engine import decide
from api.infrastructure.db.profile import PostgresProfiles
from api.tests.oracle import ORACLE, OracleCustomer, OracleProduct, credit_profile_of

# Reads the full dataset that `docker compose up` loaded, which CI never has (data/ stays out of git).
# Run: docker compose --profile test run --rm test pytest -m dataset (README.md, "Tests").
pytestmark = pytest.mark.dataset

DATASET_URL = "ALBA_DATASET_DATABASE_URL"


@pytest.fixture(scope="module")
def dataset() -> Iterator[psycopg.Connection]:
    url = os.environ.get(DATASET_URL)
    if not url:
        raise RuntimeError(f"{DATASET_URL} is not set: point it at the database the load filled")
    with psycopg.connect(url) as conn:
        yield conn


@pytest.mark.parametrize("customer", ORACLE.customers, ids=lambda c: c.customer_id)
def test_the_gold_profile_is_the_oracle_profile(dataset: psycopg.Connection, customer: OracleCustomer) -> None:
    assert PostgresProfiles(dataset).read(customer.customer_id) == credit_profile_of(customer)


@pytest.mark.parametrize("customer", ORACLE.customers, ids=lambda c: c.customer_id)
def test_the_customer_rows_are_the_oracle_rows(dataset: psycopg.Connection, customer: OracleCustomer) -> None:
    rows = dataset.execute(
        """
        SELECT c.first_name, c.last_name, c.country, c.segment, c.customer_status, c.credit_score,
               c.estimated_monthly_income, c.email IS NOT NULL,
               g.first_name, g.last_name, g.country, g.segment
        FROM customers c JOIN customer_credit_profile g USING (customer_id)
        WHERE c.customer_id = %s
        """,
        (customer.customer_id,),
    ).fetchall()
    names = (customer.first_name, customer.last_name, customer.country, customer.segment)
    assert rows == [
        (
            *names,
            customer.customer_status,
            customer.credit_score,
            customer.income_local,
            customer.has_email,
            *names,
        )
    ]


@pytest.mark.parametrize("customer", ORACLE.customers, ids=lambda c: c.customer_id)
def test_the_products_are_the_oracle_products(dataset: psycopg.Connection, customer: OracleCustomer) -> None:
    rows = dataset.execute(
        """
        SELECT product_id, product_type, currency, current_balance, product_status, days_past_due
        FROM products
        WHERE customer_id = %s
        ORDER BY product_id
        """,
        (customer.customer_id,),
    ).fetchall()
    loaded = tuple(
        OracleProduct(
            product_id=product_id,
            product_type=product_type,
            currency=currency,
            current_balance=balance,
            product_status=status,
            days_past_due=days,
        )
        for product_id, product_type, currency, balance, status, days in rows
    )
    assert loaded == customer.products


@pytest.mark.parametrize("customer", ORACLE.customers, ids=lambda c: c.customer_id)
@pytest.mark.parametrize("product", get_args(ProductKey))
def test_the_loaded_profile_reaches_the_oracle_outcome(
    dataset: psycopg.Connection, customer: OracleCustomer, product: ProductKey
) -> None:
    profile = PostgresProfiles(dataset).read(customer.customer_id)
    assert profile is not None
    decision = decide(profile, product, None)
    assert (decision.outcome, decision.deciding_rule) == (customer.expected.outcome, customer.expected.deciding_rule)


def test_the_consultant_row_is_the_oracle_consultant(dataset: psycopg.Connection) -> None:
    cesar = ORACLE.consultant
    rows = dataset.execute(
        """
        SELECT agent_id, employee_code, first_name, last_name, agent_status, specialty, email IS NOT NULL
        FROM service_agents
        WHERE agent_id = %s
        """,
        (cesar.consultant_id,),
    ).fetchall()
    assert rows == [
        (
            cesar.consultant_id,
            cesar.employee_code,
            cesar.first_name,
            cesar.last_name,
            cesar.status,
            cesar.specialty,
            cesar.has_email,
        )
    ]


def test_the_rates_of_the_as_of_date_are_the_oracle_rates(dataset: psycopg.Connection) -> None:
    rows = dataset.execute(
        "SELECT source_currency, exchange_rate FROM daily_exchange_rates WHERE date = %s AND target_currency = 'USD'",
        (ORACLE.as_of,),
    ).fetchall()
    assert dict(rows) == ORACLE.rates_to_usd


def test_the_product_types_are_the_oracle_types(dataset: psycopg.Connection) -> None:
    rows = dataset.execute("SELECT DISTINCT product_type FROM products").fetchall()
    assert sorted(product_type for (product_type,) in rows) == sorted(ORACLE.product_types)
