from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from api.contract_models import DecidedBy, EndReason, ProcessState
from api.domain.process.case import (
    NO_INCOME_FACTS,
    CaseRow,
    CertificateView,
    IncomeFacts,
    certificate_of,
    facts_by_name,
    income_facts,
    is_policy_no,
)
from api.domain.process.stored_events import Payload

EVENT_ID = UUID("33333333-3333-4333-8333-333333333333")
PROCESS_ID = UUID("11111111-1111-4111-8111-111111111111")
AS_OF = "2026-06-17"


def fact(name: str, value: object, source: str = "customer_credit_profile") -> Payload:
    return {"name": name, "value": value, "source": source, "as_of": AS_OF}


JUAN_FACTS = [
    fact("credit_score", 812),
    fact("income_local", Decimal("306753.45")),
    fact("income_currency", "MXN"),
    fact("income_usd", Decimal("17988.33")),
]
ANALYSIS: Payload = {"product": "personal_loan", "facts": JUAN_FACTS}


def decided(decided_by: DecidedBy) -> Payload:
    return {"decided_by": decided_by, "locale": "es", "outcome": "NOT_PREQUALIFIED", "body": "No precalificas."}


def test_a_policy_certificate_shows_the_income_and_product_of_its_analysis() -> None:
    assert certificate_of(EVENT_ID, decided("policy"), ANALYSIS, "credit_card") == CertificateView(
        event_id=EVENT_ID,
        decided_by="policy",
        locale="es",
        outcome="NOT_PREQUALIFIED",
        body="No precalificas.",
        product="personal_loan",
        income=IncomeFacts(Decimal("306753.45"), "MXN", Decimal("17988.33"), date(2026, 6, 17)),
    )


def test_a_consultant_certificate_shows_no_income_and_the_case_product() -> None:
    view = certificate_of(EVENT_ID, decided("consultant"), None, "credit_card")
    assert (view.decided_by, view.product, view.income) == ("consultant", "credit_card", NO_INCOME_FACTS)


def test_a_policy_certificate_without_its_analysis_fails_loud() -> None:
    with pytest.raises(ValueError, match=f"the policy certificate {EVENT_ID} names no analysis"):
        certificate_of(EVENT_ID, decided("policy"), None, "credit_card")


def test_a_consultant_certificate_that_names_an_analysis_fails_loud() -> None:
    with pytest.raises(ValueError, match=f"the consultant certificate {EVENT_ID} names an analysis"):
        certificate_of(EVENT_ID, decided("consultant"), ANALYSIS, "credit_card")


def test_the_facts_are_read_by_name_in_any_order() -> None:
    assert income_facts(list(reversed(JUAN_FACTS))) == income_facts(JUAN_FACTS)


def test_a_stated_income_has_no_usd_equivalent() -> None:
    stated = [fact("income_local", 45000, "self_declared"), fact("income_currency", "MXN"), fact("income_usd", None)]
    assert income_facts(stated) == IncomeFacts(Decimal(45000), "MXN", None, date(2026, 6, 17))


@pytest.mark.parametrize(
    ("facts", "error", "kind"),
    [
        (None, "facts must be a list of facts", TypeError),
        ([1], "facts must be a list of facts", TypeError),
        ([*JUAN_FACTS, fact("income_usd", None)], "a fact is cited twice", ValueError),
        (JUAN_FACTS[:2], r"the analysis does not cite \['income_currency', 'income_usd'\]", ValueError),
        ([{"value": 1}], "payload has no name", ValueError),
    ],
    ids=["missing", "not facts", "twice", "uncited", "unnamed"],
)
def test_facts_that_are_not_the_engines_fail_loud(facts: object, error: str, kind: type[Exception]) -> None:
    with pytest.raises(kind, match=error):
        facts_by_name(facts)


@pytest.mark.parametrize(
    ("value", "error", "kind"),
    [("45000", "income_local must be read as Decimal, got str", TypeError), (-1, "income_local -1 is not", ValueError)],
)
def test_an_income_that_is_not_an_amount_fails_loud(value: object, error: str, kind: type[Exception]) -> None:
    with pytest.raises(kind, match=error):
        income_facts([fact("income_local", value), fact("income_currency", "MXN"), fact("income_usd", None)])


def case(state: ProcessState, end_reason: EndReason | None) -> CaseRow:
    return CaseRow(PROCESS_ID, "CLI-ZGOY1V6ZC46J", state, end_reason, "credit_card", "es")


def certificate(decided_by: DecidedBy) -> CertificateView:
    return certificate_of(EVENT_ID, decided(decided_by), ANALYSIS if decided_by == "policy" else None, "credit_card")


def test_an_ended_no_the_policy_decided_is_a_policy_no() -> None:
    assert is_policy_no(case("ended", "not_prequalified"), certificate("policy")) is True


@pytest.mark.parametrize(
    ("row", "decided_by"),
    [
        (case("ended", "prequalified"), "policy"),
        (case("ended", "not_prequalified"), "consultant"),
        (case("human_active", None), "policy"),
    ],
    ids=["a yes", "a consultant's no", "an open case"],
)
def test_anything_else_is_not_a_policy_no(row: CaseRow, decided_by: DecidedBy) -> None:
    assert is_policy_no(row, certificate(decided_by)) is False


def test_a_case_with_no_certificate_is_not_a_policy_no() -> None:
    assert is_policy_no(case("ended", "not_prequalified"), None) is False
