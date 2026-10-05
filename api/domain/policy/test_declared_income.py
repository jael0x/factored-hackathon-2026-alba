from datetime import date
from decimal import Decimal

import pytest

from api.contract_models import IncomeCurrency
from api.domain.policy.declared_income import income_for_run
from api.domain.policy.engine import CreditProfile

MEXICAN = CreditProfile(
    customer_status="Active",
    credit_score=714,
    income_local=None,
    income_currency="MXN",
    income_usd=None,
    max_days_past_due=0,
    has_active_card=False,
    has_active_personal_loan=False,
    as_of=date(2026, 6, 17),
)


@pytest.mark.parametrize("currency", [None, "MXN"], ids=["pesos", "the country's currency"])
def test_an_amount_in_the_country_currency_or_in_plain_pesos_is_this_runs_income(
    currency: IncomeCurrency | None,
) -> None:
    assert income_for_run(MEXICAN, Decimal(45000), currency) == Decimal(45000)


@pytest.mark.parametrize("currency", ["COP", "ARS"])
def test_an_amount_in_another_countrys_currency_is_not_an_income(currency: IncomeCurrency) -> None:
    assert income_for_run(MEXICAN, Decimal(45000), currency) is None


def test_no_amount_stays_no_amount() -> None:
    assert income_for_run(MEXICAN, None, None) is None
