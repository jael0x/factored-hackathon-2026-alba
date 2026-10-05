from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from api.application.processes import CaseNotFound, Events
from api.contract_models import Locale
from api.domain.process.case import CaseRow, CertificateView, ThreadLine
from api.domain.process.commands import DECIDED_BY_POLICY
from api.domain.process.events import appeal_key
from api.domain.process.lifecycle import ENDED, NOT_PREQUALIFIED_END, ProcessRow
from api.domain.process.new_events import AppendResult, appeal_requested


class Cases(Protocol):
    def read_case(self, process_id: UUID) -> CaseRow | None: ...

    def of_customer(self, customer_id: str) -> list[CaseRow]: ...


class Threads(Protocol):
    def thread(self, process_id: UUID) -> list[ThreadLine]: ...

    def certificate(self, process_id: UUID) -> CertificateView | None: ...


@dataclass(frozen=True)
class CaseView:
    case: CaseRow
    thread: list[ThreadLine]
    certificate: CertificateView | None


def read_customer_case(cases: Cases, threads: Threads, customer_id: str, process_id: UUID) -> CaseView | None:
    case = cases.read_case(process_id)
    if case is None or case.customer_id != customer_id:
        return None
    return CaseView(case, threads.thread(process_id), threads.certificate(process_id))


def list_customer_cases(cases: Cases, customer_id: str) -> list[CaseRow]:
    return cases.of_customer(customer_id)


class CaseNotAppealable(Exception):
    def __init__(self, process_id: UUID) -> None:
        super().__init__(f"process {process_id} is not a no the policy decided")


# A customer may ask a person to review a no the policy decided, once (D25). None means it was already asked.
def appeal_customer_case(
    events: Events, cases: Cases, threads: Threads, customer_id: str, process_id: UUID, locale: Locale
) -> AppendResult | None:
    case = cases.read_case(process_id)
    if case is None or case.customer_id != customer_id:
        raise CaseNotFound(process_id)
    if events.has_key(appeal_key(process_id)):
        return None
    certificate = threads.certificate(process_id)
    decided_by_policy = certificate is not None and certificate.decided_by == DECIDED_BY_POLICY
    if case.state != ENDED or case.end_reason != NOT_PREQUALIFIED_END or not decided_by_policy or case.product is None:
        raise CaseNotAppealable(process_id)
    process = ProcessRow(process_id, customer_id, case.state)
    return events.append(appeal_requested(process, locale, case.product))
