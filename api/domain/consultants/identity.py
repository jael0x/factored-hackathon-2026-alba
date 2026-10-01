from dataclasses import dataclass


@dataclass(frozen=True)
class ConsultantIdentity:
    consultant_id: str
    employee_code: str
    first_name: str
    last_name: str
    email: str
    status: str
    specialty: str | None


@dataclass(frozen=True)
class ConsultantHit:
    consultant_id: str
    employee_code: str
    first_name: str
    last_name: str
    email: str
