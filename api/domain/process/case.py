from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from api.contract_models import (
    CloseOutcome,
    DecidedBy,
    EndReason,
    IncomeCurrency,
    Locale,
    MessageAuthor,
    ProcessState,
    ProductKey,
)


@dataclass(frozen=True)
class CaseRow:
    process_id: UUID
    customer_id: str
    state: ProcessState
    end_reason: EndReason | None
    product: ProductKey | None
    locale: Locale


# One line of the thread: a customer message is its event, an assistant or template line its messages row.
@dataclass(frozen=True)
class ThreadLine:
    line_id: UUID
    author: MessageAuthor
    body: str
    event_id: UUID


# The certificate a customer reads: the decision's text, and the income the run read (D24 (7)).
@dataclass(frozen=True)
class CertificateView:
    event_id: UUID
    decided_by: DecidedBy
    locale: Locale
    outcome: CloseOutcome
    body: str
    product: ProductKey | None
    income_local: Decimal | None
    income_currency: IncomeCurrency | None
    income_usd: Decimal | None
    as_of: date | None
