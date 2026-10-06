from typing import get_args

import pytest

from api.contract_models import Outcome, ProductKey
from api.domain.policy.engine import CREDIT_CARD, R02, decide
from api.tests.cycle_harness import JULIANA, MARIANA
from api.tests.oracle import ORACLE, OracleCustomer, credit_profile_of, oracle_customer

PRODUCTS: tuple[ProductKey, ...] = get_args(ProductKey)
CASES = [(customer, product) for customer in ORACLE.customers for product in PRODUCTS]


def case_id(value: object) -> str:
    return value.customer_id if isinstance(value, OracleCustomer) else str(value)


def test_the_four_customers_cover_every_outcome_once() -> None:
    assert sorted(c.expected.outcome for c in ORACLE.customers) == sorted(get_args(Outcome))


@pytest.mark.parametrize(("customer", "product"), CASES, ids=case_id)
def test_the_policy_reaches_the_oracle_outcome(customer: OracleCustomer, product: ProductKey) -> None:
    decision = decide(credit_profile_of(customer), product, None)
    assert (decision.outcome, decision.deciding_rule) == (customer.expected.outcome, customer.expected.deciding_rule)


@pytest.mark.parametrize(
    ("customer", "product"),
    [(c, p) for c, p in CASES if c.after_declared_income is not None],
    ids=case_id,
)
def test_a_stated_income_reaches_the_oracle_outcome(customer: OracleCustomer, product: ProductKey) -> None:
    after = customer.after_declared_income
    assert after is not None
    decision = decide(credit_profile_of(customer), product, after.declared_income)
    assert (decision.outcome, decision.deciding_rule) == (after.outcome, after.deciding_rule)


def test_mariana_holds_a_card_and_is_still_decided_by_delinquency() -> None:
    mariana = oracle_customer(MARIANA)
    assert mariana.has_active_card
    assert decide(credit_profile_of(mariana), CREDIT_CARD, None).deciding_rule == R02


def test_only_juliana_states_an_income() -> None:
    assert [c.customer_id for c in ORACLE.customers if c.after_declared_income is not None] == [JULIANA]
