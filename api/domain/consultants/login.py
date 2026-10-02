from dataclasses import dataclass

from api.domain.consultants.identity import ConsultantIdentity

ACTIVE_STATUS = "Active"


@dataclass(frozen=True)
class ConsultantLoginKey:
    email: str
    employee_code: str


def login_key(email: str, employee_code: str) -> ConsultantLoginKey:
    return ConsultantLoginKey(email=email.strip().lower(), employee_code=employee_code.strip().upper())


def can_receive_code(consultant: ConsultantIdentity) -> bool:
    return consultant.status == ACTIVE_STATUS
