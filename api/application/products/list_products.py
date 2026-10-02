from typing import Protocol

from api.domain.products.listing import is_listed
from api.domain.products.product import CustomerProduct


class Products(Protocol):
    def of_customer(self, customer_id: str) -> list[CustomerProduct]: ...


def list_products(
    products: Products, session_customer_id: str, requested_customer_id: str | None
) -> list[CustomerProduct]:
    if requested_customer_id is not None and requested_customer_id != session_customer_id:
        return []
    return [product for product in products.of_customer(session_customer_id) if is_listed(product)]
