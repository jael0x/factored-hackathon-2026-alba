from api.application.session.ports import Customers
from api.domain.customers.identity import CustomerIdentity


def read_current_customer(customers: Customers, customer_id: str) -> CustomerIdentity | None:
    return customers.find_by_id(customer_id)
