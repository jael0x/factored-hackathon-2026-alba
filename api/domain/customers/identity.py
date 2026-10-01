from dataclasses import dataclass


@dataclass(frozen=True)
class CustomerIdentity:
    customer_id: str
    first_name: str
    last_name: str
    email: str | None


@dataclass(frozen=True)
class CustomerHit:
    customer_id: str
    document_number: str
    first_name: str
    last_name: str
    country: str
