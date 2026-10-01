from datetime import datetime

from api.application.session.ports import Consultants, Customers, LoginCodes
from api.domain.consultants.login import can_receive_code, login_key
from api.domain.session import codes
from api.domain.session.codes import CodeDelivery
from api.domain.session.tokens import CONSULTANT, CUSTOMER, Role


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
    return store_new_code(login_codes, secret, customer.customer_id, CUSTOMER, customer.email, now)


def issue_consultant_code(
    consultants: Consultants,
    login_codes: LoginCodes,
    secret: str,
    email: str,
    employee_code: str,
    now: datetime,
) -> CodeDelivery | None:
    consultant = consultants.find_by_login(login_key(email, employee_code))
    if consultant is None or not can_receive_code(consultant):
        return None
    return store_new_code(login_codes, secret, consultant.consultant_id, CONSULTANT, consultant.email, now)


def store_new_code(
    login_codes: LoginCodes, secret: str, subject_id: str, role: Role, email: str, now: datetime
) -> CodeDelivery:
    code = codes.new_code()
    login_codes.store(subject_id, role, codes.hash_code(secret, subject_id, code), now)
    return CodeDelivery(email=email, code=code)
