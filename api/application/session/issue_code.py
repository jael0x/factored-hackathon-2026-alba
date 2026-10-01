from datetime import datetime

from api.application.session.ports import Customers, LoginCodes
from api.domain.session import codes
from api.domain.session.codes import CodeDelivery
from api.domain.session.tokens import CUSTOMER


def issue_customer_code(
    customers: Customers,
    login_codes: LoginCodes,
    secret: str,
    document_number: str,
    now: datetime,
) -> CodeDelivery | None:
    customer = customers.find_by_document(document_number)
    if customer is None or customer.email is None:
        return None
    code = codes.new_code()
    login_codes.store(customer.customer_id, CUSTOMER, codes.hash_code(secret, customer.customer_id, code), now)
    return CodeDelivery(email=customer.email, code=code)
