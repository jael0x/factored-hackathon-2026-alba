from dataclasses import replace
from decimal import Decimal

import pytest

from api.domain.products.listing import is_listed
from api.domain.products.product import CustomerProduct

MORTGAGE = CustomerProduct("PRD-W1ZJKF7U5B6C", "Préstamo Hipotecario", "LOAN-31561597", "USD", Decimal("109159.57"), "Active")
PERSONAL_LOAN = CustomerProduct("PRD-TESTLOAN0001", "Préstamo Personal", "LOAN-20000001", "COP", Decimal("8500000.00"), "Active")
SAVINGS = CustomerProduct("PRD-AQZ0094E1XY0", "Cuenta Ahorro", "8482915725", "USD", Decimal("1559.57"), "Active")
CREDIT_CARD = CustomerProduct("PRD-TESTCARD0001", "Tarjeta Crédito", "4111111111115476", "ARS", Decimal("125000.00"), "Active")


@pytest.mark.parametrize("product", [MORTGAGE, PERSONAL_LOAN, SAVINGS, CREDIT_CARD])
def test_an_open_product_with_a_balance_is_listed(product: CustomerProduct) -> None:
    assert is_listed(product) is True


@pytest.mark.parametrize("product", [MORTGAGE, PERSONAL_LOAN, SAVINGS, CREDIT_CARD])
def test_a_closed_product_is_not_listed(product: CustomerProduct) -> None:
    assert is_listed(replace(product, product_status="Closed")) is False


@pytest.mark.parametrize("status", ["Active", "Blocked", "Suspended"])
@pytest.mark.parametrize("loan", [MORTGAGE, PERSONAL_LOAN])
def test_a_loan_at_zero_is_paid_and_not_listed(loan: CustomerProduct, status: str) -> None:
    assert is_listed(replace(loan, current_balance=Decimal("0.00"), product_status=status)) is False


@pytest.mark.parametrize("product", [SAVINGS, CREDIT_CARD])
def test_a_product_that_is_not_a_loan_is_listed_at_zero(product: CustomerProduct) -> None:
    assert is_listed(replace(product, current_balance=Decimal("0.00"))) is True


@pytest.mark.parametrize("status", ["Blocked", "Suspended"])
def test_a_blocked_or_suspended_product_is_listed(status: str) -> None:
    assert is_listed(replace(SAVINGS, product_status=status)) is True
