from datetime import datetime

from api.application.session.ports import Consultants, Customers, LoginCodes
from api.domain.consultants.login import can_receive_code, login_key
from api.domain.session import codes
from api.domain.session.tokens import CONSULTANT, CUSTOMER, Role, SessionClaims


def open_customer_session(
    customers: Customers,
    login_codes: LoginCodes,
    secret: str,
    document_number: str,
    code: str,
    now: datetime,
) -> SessionClaims | None:
    customer = customers.find_by_document(document_number)
    if customer is None or not redeem_code(login_codes, secret, customer.customer_id, CUSTOMER, code, now):
        return None
    return SessionClaims(sub=customer.customer_id, role=CUSTOMER)


def open_consultant_session(
    consultants: Consultants,
    login_codes: LoginCodes,
    secret: str,
    email: str,
    employee_code: str,
    code: str,
    now: datetime,
) -> SessionClaims | None:
    consultant = consultants.find_by_login(login_key(email, employee_code))
    if consultant is None or not can_receive_code(consultant):
        return None
    if not redeem_code(login_codes, secret, consultant.consultant_id, CONSULTANT, code, now):
        return None
    return SessionClaims(sub=consultant.consultant_id, role=CONSULTANT)


def redeem_code(login_codes: LoginCodes, secret: str, subject_id: str, role: Role, code: str, now: datetime) -> bool:
    issued = login_codes.latest(subject_id, role)
    if issued is None or not codes.code_is_open(issued, now):
        return False
    if not codes.code_matches(secret, subject_id, issued, code):
        login_codes.record_wrong(issued.id)
        return False
    return login_codes.spend(issued.id, now)
