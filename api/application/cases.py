from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from api.application.processes import CaseAlreadyOpen, CaseNotFound, Events
from api.contract_models import Locale, ProcessKey, ProductKey
from api.domain.process.case import CaseRow, CertificateView, ThreadLine, is_policy_no
from api.domain.process.events import appeal_key
from api.domain.process.lifecycle import CREDIT_PREQUALIFICATION, ProcessRow
from api.domain.process.new_events import AppendResult, appeal_requested


class Cases(Protocol):
    def read_case(self, customer_id: str, process_id: UUID) -> CaseRow | None: ...

    def of_customer(self, customer_id: str) -> list[CaseRow]: ...

    def find_open(self, customer_id: str, process_key: ProcessKey, product: ProductKey) -> ProcessRow | None: ...


class Threads(Protocol):
    def thread(self, customer_id: str, process_id: UUID) -> list[ThreadLine]: ...

    def certificate(self, customer_id: str, process_id: UUID) -> CertificateView | None: ...


@dataclass(frozen=True)
class CaseView:
    case: CaseRow
    thread: list[ThreadLine]
    certificate: CertificateView | None
    appealable: bool


class CaseNotAppealable(Exception):
    def __init__(self, process_id: UUID) -> None:
        super().__init__(f"process {process_id} is not a no the policy decided")


def read_customer_case(cases: Cases, threads: Threads, customer_id: str, process_id: UUID) -> CaseView | None:
    case = cases.read_case(customer_id, process_id)
    if case is None:
        return None
    certificate = threads.certificate(customer_id, process_id)
    appealable = not isinstance(appeal_check(cases, case, certificate), Exception)
    return CaseView(case, threads.thread(customer_id, process_id), certificate, appealable)


def list_customer_cases(cases: Cases, customer_id: str) -> list[CaseRow]:
    return cases.of_customer(customer_id)


# Reopening takes the product's one open case, so an appeal waits while another case of it is open (D25).
def appeal_check(
    cases: Cases, case: CaseRow, certificate: CertificateView | None
) -> ProductKey | CaseNotAppealable | CaseAlreadyOpen:
    if case.product is None or not is_policy_no(case, certificate):
        return CaseNotAppealable(case.process_id)
    if cases.find_open(case.customer_id, CREDIT_PREQUALIFICATION, case.product) is not None:
        return CaseAlreadyOpen(case.product)
    return case.product


# A customer may ask a person to review a no the policy decided, once (D25). None means it was already asked.
def appeal_customer_case(
    events: Events, cases: Cases, threads: Threads, customer_id: str, process_id: UUID, locale: Locale
) -> AppendResult | None:
    case = cases.read_case(customer_id, process_id)
    if case is None:
        raise CaseNotFound(process_id)
    if events.has_key(appeal_key(process_id)):
        return None
    product = appeal_check(cases, case, threads.certificate(customer_id, process_id))
    if isinstance(product, Exception):
        raise product
    process = ProcessRow(process_id, customer_id, case.state)
    return events.append(appeal_requested(process, locale, product))
