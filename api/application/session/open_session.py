from datetime import datetime

from api.application.session.ports import Customers, LoginCodes
from api.domain.session import codes
from api.domain.session.tokens import CUSTOMER, SessionClaims


def open_customer_session(
    customers: Customers,
    login_codes: LoginCodes,
    secret: str,
    document_number: str,
    code: str,
    now: datetime,
) -> SessionClaims | None:
    customer = customers.find_by_document(document_number)
    if customer is None:
        return None
    issued = login_codes.latest(customer.customer_id, CUSTOMER)
    if issued is None or not codes.code_is_open(issued, now):
        return None
    if not codes.code_matches(secret, customer.customer_id, issued, code):
        login_codes.record_wrong(issued.id)
        return None
    if not login_codes.spend(issued.id, now):
        return None
    return SessionClaims(sub=customer.customer_id, role=CUSTOMER)
