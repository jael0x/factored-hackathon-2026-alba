from datetime import datetime
from typing import Protocol
from uuid import UUID

from api.domain.customers.identity import CustomerIdentity
from api.domain.session.codes import IssuedCode
from api.domain.session.tokens import Role


class Customers(Protocol):
    def find_by_document(self, document_number: str) -> CustomerIdentity | None: ...

    def find_by_id(self, customer_id: str) -> CustomerIdentity | None: ...


class LoginCodes(Protocol):
    def store(self, subject_id: str, role: Role, code_hash: str, now: datetime) -> None: ...

    def latest(self, subject_id: str, role: Role) -> IssuedCode | None: ...

    def record_wrong(self, code_id: UUID) -> None: ...

    def spend(self, code_id: UUID, now: datetime) -> bool: ...
