from datetime import datetime
from typing import Protocol
from uuid import UUID

from api.contract_models import Role
from api.domain.consultants.identity import ConsultantIdentity
from api.domain.consultants.login import ConsultantLoginKey
from api.domain.customers.identity import CustomerIdentity
from api.domain.session.codes import IssuedCode


class Customers(Protocol):
    def find_by_document(self, document_number: str) -> CustomerIdentity | None: ...

    def find_by_id(self, customer_id: str) -> CustomerIdentity | None: ...


class Consultants(Protocol):
    def find_by_login(self, key: ConsultantLoginKey) -> ConsultantIdentity | None: ...

    def find_by_id(self, consultant_id: str) -> ConsultantIdentity | None: ...


class LoginCodes(Protocol):
    def store(self, subject_id: str, role: Role, code_hash: str, now: datetime) -> None: ...

    def latest(self, subject_id: str, role: Role) -> IssuedCode | None: ...

    def record_wrong(self, code_id: UUID) -> None: ...

    def spend(self, code_id: UUID, now: datetime) -> bool: ...
