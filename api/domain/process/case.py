from collections.abc import Mapping
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
from api.domain.closed_sets import parse_member
from api.domain.locale import LOCALES
from api.domain.policy.engine import INCOME_CURRENCY, INCOME_LOCAL, INCOME_USD
from api.domain.process.commands import DECIDED_BY_POLICY
from api.domain.process.lifecycle import ENDED, NOT_PREQUALIFIED_END
from api.domain.process.stored_events import (
    CLOSE_OUTCOMES,
    DECIDED_BY,
    PRODUCT_KEYS,
    Payload,
    field,
    parse_amount,
    parse_optional_currency,
    require_str,
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


@dataclass(frozen=True)
class IncomeFacts:
    income_local: Decimal | None
    income_currency: IncomeCurrency | None
    income_usd: Decimal | None
    as_of: date | None


NO_INCOME_FACTS = IncomeFacts(None, None, None, None)


@dataclass(frozen=True)
class CertificateView:
    event_id: UUID
    decided_by: DecidedBy
    locale: Locale
    outcome: CloseOutcome
    body: str
    product: ProductKey | None
    income: IncomeFacts


# A policy certificate shows the income of the analysis its decision names in caused_by_event_id; a consultant's
# decision is the person's, so it shows none, and its product is the case's (PLAN.md D25).
def certificate_of(
    event_id: UUID, decided: Payload, analysis: Payload | None, case_product: ProductKey | None
) -> CertificateView:
    decided_by = parse_member(field(decided, "decided_by"), DECIDED_BY, "decided_by")
    if (decided_by == DECIDED_BY_POLICY) != (analysis is not None):
        linked = "names no analysis" if analysis is None else "names an analysis"
        raise ValueError(f"the {decided_by} certificate {event_id} {linked}")
    return CertificateView(
        event_id=event_id,
        decided_by=decided_by,
        locale=parse_member(field(decided, "locale"), LOCALES, "locale"),
        outcome=parse_member(field(decided, "outcome"), CLOSE_OUTCOMES, "outcome"),
        body=require_str(field(decided, "body"), "body"),
        product=case_product if analysis is None else parse_member(field(analysis, "product"), PRODUCT_KEYS, "product"),
        income=NO_INCOME_FACTS if analysis is None else income_facts(field(analysis, "facts")),
    )


# Every decision cites these facts once, after the closing one (ARCHITECTURE.md, "Policy alba-credit-v1").
def income_facts(facts: object) -> IncomeFacts:
    cited = facts_by_name(facts)
    income = cited[INCOME_LOCAL]
    return IncomeFacts(
        income_local=parse_amount(field(income, "value"), INCOME_LOCAL),
        income_currency=parse_optional_currency(field(cited[INCOME_CURRENCY], "value"), INCOME_CURRENCY),
        income_usd=parse_amount(field(cited[INCOME_USD], "value"), INCOME_USD),
        as_of=date.fromisoformat(require_str(field(income, "as_of"), "as_of")),
    )


def facts_by_name(facts: object) -> Mapping[str, Payload]:
    if not isinstance(facts, list) or not all(isinstance(item, Mapping) for item in facts):
        raise TypeError(f"facts must be a list of facts, got {facts!r}")
    names = [require_str(field(item, "name"), "fact name") for item in facts]
    if len(names) != len(set(names)):
        raise ValueError(f"a fact is cited twice: {sorted(names)}")
    missing = {INCOME_LOCAL, INCOME_CURRENCY, INCOME_USD} - set(names)
    if missing:
        raise ValueError(f"the analysis does not cite {sorted(missing)}")
    return dict(zip(names, facts, strict=True))


# A no the policy decided is the only result a customer may send to a person (PLAN.md D25).
def is_policy_no(case: CaseRow, certificate: CertificateView | None) -> bool:
    return (
        case.state == ENDED
        and case.end_reason == NOT_PREQUALIFIED_END
        and certificate is not None
        and certificate.decided_by == DECIDED_BY_POLICY
    )
