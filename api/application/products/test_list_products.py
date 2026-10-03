from decimal import Decimal

from api.application.products.list_products import list_products
from api.domain.products.product import CustomerProduct

JUAN = "CLI-9EDEKZ8OUNUR"
ALICIA = "CLI-440CO5FZIY6A"
JUAN_SAVINGS = CustomerProduct("PRD-AQZ0094E1XY0", "Cuenta Ahorro", "8482915725", "USD", Decimal("1559.57"), "Active")
ALICIA_CHECKING = CustomerProduct(
    "PRD-HSUB9M7052JT", "Cuenta Corriente", "5964932955", "COP", Decimal("13192324.57"), "Active"
)
ALICIA_CLOSED_SAVINGS = CustomerProduct(
    "PRD-YT0DEZDUN1I4", "Cuenta Ahorro", "2079790665", "COP", Decimal("1419507.66"), "Closed"
)


class MemProducts:
    def __init__(self) -> None:
        self.asked: list[str] = []

    def of_customer(self, customer_id: str) -> list[CustomerProduct]:
        self.asked.append(customer_id)
        return {JUAN: [JUAN_SAVINGS], ALICIA: [ALICIA_CHECKING, ALICIA_CLOSED_SAVINGS]}.get(customer_id, [])


def test_without_an_id_the_session_customer_gets_their_products() -> None:
    products = MemProducts()
    assert list_products(products, JUAN, None) == [JUAN_SAVINGS]
    assert products.asked == [JUAN]


def test_asking_for_ones_own_id_gets_ones_own_products() -> None:
    products = MemProducts()
    assert list_products(products, JUAN, JUAN) == [JUAN_SAVINGS]
    assert products.asked == [JUAN]


def test_asking_for_another_customers_id_returns_nothing_and_reads_nothing() -> None:
    products = MemProducts()
    assert list_products(products, JUAN, ALICIA) == []
    assert products.asked == []


def test_products_the_customer_does_not_see_are_left_out() -> None:
    assert list_products(MemProducts(), ALICIA, None) == [ALICIA_CHECKING]
