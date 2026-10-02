from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import get_args

import pytest

from api.contract_models import (
    IncomeCurrency,
    Outcome,
    ProductKey,
    RuleId,
    RuleTraceResult,
)
from api.domain.policy.engine import (
    ALBA_CREDIT_V1,
    CREDIT_CARD,
    CREDIT_SCORE,
    CUSTOMER_STATUS,
    DECLARED_INCOME,
    HOLDS_BY_PRODUCT,
    HOLDS_PRODUCT,
    INCOME_CURRENCY,
    INCOME_LOCAL,
    MAX_DAYS_PAST_DUE,
    NEEDS_INFO,
    NOT_PREQUALIFIED,
    PASSED,
    PERSONAL_LOAN,
    POLICY_PATH,
    PREQUALIFIED,
    R01,
    R02,
    R03,
    R04,
    R05,
    R06,
    R09,
    REFER,
    RULES,
    SELF_DECLARED,
    SOURCE_DAYS,
    SOURCE_INCOME,
    SOURCE_PRODUCTS,
    SOURCE_SCORE,
    SOURCE_SELF_DECLARED,
    SOURCE_STATUS,
    CreditProfile,
    CustomerStatus,
    Decision,
    DelinquencyBands,
    PolicyFact,
    ScoreBands,
    StatusRules,
    TraceStep,
    TraceValue,
    decide,
    decide_under,
    load_policy,
    parse_customer_status,
    parse_declared_income,
    parse_product,
    terminal_step,
)

AS_OF = date(2026, 6, 17)
FILE_INCOME = Decimal(1000)


def profile(
    *,
    customer_status: CustomerStatus = "Active",
    credit_score: int | None = 750,
    income_local: Decimal | None = FILE_INCOME,
    income_currency: IncomeCurrency | None = "MXN",
    income_usd: Decimal | None = Decimal("58.64"),
    max_days_past_due: int = 0,
    has_active_card: bool = False,
    has_active_personal_loan: bool = False,
) -> CreditProfile:
    return CreditProfile(
        customer_status=customer_status,
        credit_score=credit_score,
        income_local=income_local,
        income_currency=income_currency,
        income_usd=income_usd,
        max_days_past_due=max_days_past_due,
        has_active_card=has_active_card,
        has_active_personal_loan=has_active_personal_loan,
        as_of=AS_OF,
    )


def fact(name: str, value: TraceValue, source: str) -> PolicyFact:
    return PolicyFact(name=name, value=value, source=source, as_of=AS_OF)


def policy_file(tmp_path: Path, old: str, new: str) -> Path:
    source = POLICY_PATH.read_text(encoding="utf-8")
    assert old in source
    path = tmp_path / "alba-credit-v1.yaml"
    path.write_text(source.replace(old, new, 1), encoding="utf-8")
    return path


def test_every_rule_id_has_an_implementation() -> None:
    assert set(RULES) == set(get_args(RuleId))


def test_every_product_key_has_a_holding_flag() -> None:
    assert set(HOLDS_BY_PRODUCT) == set(get_args(ProductKey))


def test_decide_runs_the_policy_file() -> None:
    assert ALBA_CREDIT_V1 == load_policy()


def test_terminal_trace_results_are_exactly_the_outcomes() -> None:
    assert set(get_args(RuleTraceResult)) - {PASSED, SELF_DECLARED} == set(get_args(Outcome))


def test_fact_sources_cite_the_contract_columns() -> None:
    assert SOURCE_STATUS == "customer_credit_profile.customer_status"
    assert SOURCE_SCORE == "customer_credit_profile.credit_score"
    assert SOURCE_DAYS == "customer_credit_profile.max_days_past_due"
    assert SOURCE_INCOME == "customer_credit_profile.income_local"
    assert SOURCE_PRODUCTS == "products"
    assert SOURCE_SELF_DECLARED == "self_declared"


def test_the_policy_file_holds_the_contract_thresholds() -> None:
    spec = load_policy()
    assert spec.version == "alba-credit-v1"
    assert spec.rules == (R01, R02, R03, R09, R04, R06, R05)
    assert spec.status == StatusRules(
        refer=frozenset({"Suspended", "Inactive"}),
        not_prequalified=frozenset({"Closed"}),
        passed=frozenset({"Active"}),
    )
    assert spec.score == ScoreBands(refer_min=580, refer_max=619, prequalified_min=620)
    assert spec.delinquency == DelinquencyBands(refer_min=1, refer_max=29, fail_min=30)


def test_the_first_terminal_step_wins_in_sequence_order() -> None:
    delinquency = TraceStep(R02, {MAX_DAYS_PAST_DUE: 180}, NOT_PREQUALIFIED)
    score = TraceStep(R05, {CREDIT_SCORE: 515}, NOT_PREQUALIFIED)
    assert terminal_step((delinquency, score)) == delinquency
    assert terminal_step((score, delinquency)) == score


def test_none_is_an_absent_amount_and_zero_is_an_amount() -> None:
    assert parse_declared_income(None) is None
    assert parse_declared_income(Decimal(0)) == Decimal(0)


def test_a_float_is_not_a_declared_amount() -> None:
    with pytest.raises(TypeError, match="declared_income must be Decimal or None"):
        parse_declared_income(45000.0)


@pytest.mark.parametrize("amount", ["NaN", "sNaN", "Infinity", "-Infinity"])
def test_a_non_finite_declared_income_is_rejected(amount: str) -> None:
    with pytest.raises(ValueError, match="finite"):
        decide(profile(income_local=None), CREDIT_CARD, Decimal(amount))


@pytest.mark.parametrize("amount", ["-0.01", "-45000"])
def test_a_negative_declared_income_is_rejected(amount: str) -> None:
    with pytest.raises(ValueError, match="negative"):
        decide(profile(income_local=None), CREDIT_CARD, Decimal(amount))


def test_an_unknown_product_is_rejected() -> None:
    with pytest.raises(ValueError, match="product 'mortgage' is outside the policy"):
        parse_product("mortgage")


@pytest.mark.parametrize(
    ("score", "outcome"),
    [
        (579, NOT_PREQUALIFIED),
        (580, REFER),
        (619, REFER),
        (620, PREQUALIFIED),
    ],
)
def test_the_score_band_sets_the_outcome_after_every_earlier_rule_passes(score: int, outcome: Outcome) -> None:
    assert decide(profile(credit_score=score), CREDIT_CARD, None) == Decision(
        outcome=outcome,
        deciding_rule=R05,
        rule_trace=(
            TraceStep(R01, {CUSTOMER_STATUS: "Active"}, PASSED),
            TraceStep(R02, {MAX_DAYS_PAST_DUE: 0}, PASSED),
            TraceStep(R03, {MAX_DAYS_PAST_DUE: 0}, PASSED),
            TraceStep(R09, {HOLDS_PRODUCT: False}, PASSED),
            TraceStep(R04, {CREDIT_SCORE: score}, PASSED),
            TraceStep(
                R06,
                {INCOME_LOCAL: FILE_INCOME, DECLARED_INCOME: None, INCOME_CURRENCY: "MXN"},
                PASSED,
            ),
            TraceStep(R05, {CREDIT_SCORE: score}, outcome),
        ),
        facts=(fact(CREDIT_SCORE, score, SOURCE_SCORE),),
        policy_version="alba-credit-v1",
    )


def test_zero_days_past_due_does_not_close_on_delinquency() -> None:
    assert decide(profile(credit_score=620, max_days_past_due=0), CREDIT_CARD, None) == Decision(
        outcome=PREQUALIFIED,
        deciding_rule=R05,
        rule_trace=(
            TraceStep(R01, {CUSTOMER_STATUS: "Active"}, PASSED),
            TraceStep(R02, {MAX_DAYS_PAST_DUE: 0}, PASSED),
            TraceStep(R03, {MAX_DAYS_PAST_DUE: 0}, PASSED),
            TraceStep(R09, {HOLDS_PRODUCT: False}, PASSED),
            TraceStep(R04, {CREDIT_SCORE: 620}, PASSED),
            TraceStep(
                R06,
                {INCOME_LOCAL: FILE_INCOME, DECLARED_INCOME: None, INCOME_CURRENCY: "MXN"},
                PASSED,
            ),
            TraceStep(R05, {CREDIT_SCORE: 620}, PREQUALIFIED),
        ),
        facts=(fact(CREDIT_SCORE, 620, SOURCE_SCORE),),
        policy_version="alba-credit-v1",
    )


@pytest.mark.parametrize("days", [1, 29])
def test_days_past_due_from_1_to_29_refer(days: int) -> None:
    assert decide(profile(credit_score=750, max_days_past_due=days), PERSONAL_LOAN, None) == Decision(
        outcome=REFER,
        deciding_rule=R03,
        rule_trace=(
            TraceStep(R01, {CUSTOMER_STATUS: "Active"}, PASSED),
            TraceStep(R02, {MAX_DAYS_PAST_DUE: days}, PASSED),
            TraceStep(R03, {MAX_DAYS_PAST_DUE: days}, REFER),
        ),
        facts=(fact(MAX_DAYS_PAST_DUE, days, SOURCE_DAYS),),
        policy_version="alba-credit-v1",
    )


def test_thirty_days_past_due_does_not_prequalify_before_the_score() -> None:
    assert decide(profile(credit_score=750, max_days_past_due=30), PERSONAL_LOAN, None) == Decision(
        outcome=NOT_PREQUALIFIED,
        deciding_rule=R02,
        rule_trace=(
            TraceStep(R01, {CUSTOMER_STATUS: "Active"}, PASSED),
            TraceStep(R02, {MAX_DAYS_PAST_DUE: 30}, NOT_PREQUALIFIED),
        ),
        facts=(fact(MAX_DAYS_PAST_DUE, 30, SOURCE_DAYS),),
        policy_version="alba-credit-v1",
    )


@pytest.mark.parametrize(
    ("status", "outcome"),
    [("Suspended", REFER), ("Inactive", REFER), ("Closed", NOT_PREQUALIFIED)],
)
def test_customer_status_decides_before_the_score(status: CustomerStatus, outcome: Outcome) -> None:
    assert decide(profile(customer_status=status, credit_score=750), CREDIT_CARD, None) == Decision(
        outcome=outcome,
        deciding_rule=R01,
        rule_trace=(TraceStep(R01, {CUSTOMER_STATUS: status}, outcome),),
        facts=(fact(CUSTOMER_STATUS, status, SOURCE_STATUS),),
        policy_version="alba-credit-v1",
    )


def test_an_unknown_customer_status_is_rejected() -> None:
    with pytest.raises(ValueError, match="customer_status 'Frozen' is outside the policy"):
        parse_customer_status("Frozen")


def test_a_profile_with_an_unknown_customer_status_cannot_be_built() -> None:
    with pytest.raises(ValueError, match="customer_status 'Frozen' is outside the policy"):
        replace(profile(), customer_status="Frozen")  # type: ignore[arg-type]  # rows from the database are not type-checked


def test_a_customer_who_already_holds_the_card_is_referred() -> None:
    assert decide(profile(credit_score=750, has_active_card=True), CREDIT_CARD, None) == Decision(
        outcome=REFER,
        deciding_rule=R09,
        rule_trace=(
            TraceStep(R01, {CUSTOMER_STATUS: "Active"}, PASSED),
            TraceStep(R02, {MAX_DAYS_PAST_DUE: 0}, PASSED),
            TraceStep(R03, {MAX_DAYS_PAST_DUE: 0}, PASSED),
            TraceStep(R09, {HOLDS_PRODUCT: True}, REFER),
        ),
        facts=(fact(HOLDS_PRODUCT, True, SOURCE_PRODUCTS),),
        policy_version="alba-credit-v1",
    )


def test_holding_a_card_does_not_refer_a_personal_loan() -> None:
    assert decide(
        profile(credit_score=750, has_active_card=True, has_active_personal_loan=False),
        PERSONAL_LOAN,
        None,
    ) == Decision(
        outcome=PREQUALIFIED,
        deciding_rule=R05,
        rule_trace=(
            TraceStep(R01, {CUSTOMER_STATUS: "Active"}, PASSED),
            TraceStep(R02, {MAX_DAYS_PAST_DUE: 0}, PASSED),
            TraceStep(R03, {MAX_DAYS_PAST_DUE: 0}, PASSED),
            TraceStep(R09, {HOLDS_PRODUCT: False}, PASSED),
            TraceStep(R04, {CREDIT_SCORE: 750}, PASSED),
            TraceStep(
                R06,
                {INCOME_LOCAL: FILE_INCOME, DECLARED_INCOME: None, INCOME_CURRENCY: "MXN"},
                PASSED,
            ),
            TraceStep(R05, {CREDIT_SCORE: 750}, PREQUALIFIED),
        ),
        facts=(fact(CREDIT_SCORE, 750, SOURCE_SCORE),),
        policy_version="alba-credit-v1",
    )


def test_an_empty_score_refers_before_income_is_considered() -> None:
    assert decide(profile(credit_score=None, income_local=None), PERSONAL_LOAN, None) == Decision(
        outcome=REFER,
        deciding_rule=R04,
        rule_trace=(
            TraceStep(R01, {CUSTOMER_STATUS: "Active"}, PASSED),
            TraceStep(R02, {MAX_DAYS_PAST_DUE: 0}, PASSED),
            TraceStep(R03, {MAX_DAYS_PAST_DUE: 0}, PASSED),
            TraceStep(R09, {HOLDS_PRODUCT: False}, PASSED),
            TraceStep(R04, {CREDIT_SCORE: None}, REFER),
        ),
        facts=(fact(CREDIT_SCORE, None, SOURCE_SCORE),),
        policy_version="alba-credit-v1",
    )


def test_an_empty_score_with_income_on_file_still_refers_on_r04() -> None:
    assert decide(profile(credit_score=None, income_local=FILE_INCOME), PERSONAL_LOAN, None) == Decision(
        outcome=REFER,
        deciding_rule=R04,
        rule_trace=(
            TraceStep(R01, {CUSTOMER_STATUS: "Active"}, PASSED),
            TraceStep(R02, {MAX_DAYS_PAST_DUE: 0}, PASSED),
            TraceStep(R03, {MAX_DAYS_PAST_DUE: 0}, PASSED),
            TraceStep(R09, {HOLDS_PRODUCT: False}, PASSED),
            TraceStep(R04, {CREDIT_SCORE: None}, REFER),
        ),
        facts=(fact(CREDIT_SCORE, None, SOURCE_SCORE),),
        policy_version="alba-credit-v1",
    )


def test_an_empty_income_with_no_stated_amount_needs_info() -> None:
    assert decide(profile(credit_score=714, income_local=None), CREDIT_CARD, None) == Decision(
        outcome=NEEDS_INFO,
        deciding_rule=R06,
        rule_trace=(
            TraceStep(R01, {CUSTOMER_STATUS: "Active"}, PASSED),
            TraceStep(R02, {MAX_DAYS_PAST_DUE: 0}, PASSED),
            TraceStep(R03, {MAX_DAYS_PAST_DUE: 0}, PASSED),
            TraceStep(R09, {HOLDS_PRODUCT: False}, PASSED),
            TraceStep(R04, {CREDIT_SCORE: 714}, PASSED),
            TraceStep(
                R06,
                {INCOME_LOCAL: None, DECLARED_INCOME: None, INCOME_CURRENCY: "MXN"},
                NEEDS_INFO,
            ),
        ),
        facts=(fact(INCOME_LOCAL, None, SOURCE_INCOME),),
        policy_version="alba-credit-v1",
    )


def test_a_stated_income_is_marked_self_declared_and_the_score_then_decides() -> None:
    customer = profile(credit_score=714, income_local=None, income_currency="MXN", income_usd=None)
    assert decide(customer, CREDIT_CARD, Decimal(45000)) == Decision(
        outcome=PREQUALIFIED,
        deciding_rule=R05,
        rule_trace=(
            TraceStep(R01, {CUSTOMER_STATUS: "Active"}, PASSED),
            TraceStep(R02, {MAX_DAYS_PAST_DUE: 0}, PASSED),
            TraceStep(R03, {MAX_DAYS_PAST_DUE: 0}, PASSED),
            TraceStep(R09, {HOLDS_PRODUCT: False}, PASSED),
            TraceStep(R04, {CREDIT_SCORE: 714}, PASSED),
            TraceStep(
                R06,
                {INCOME_LOCAL: None, DECLARED_INCOME: Decimal(45000), INCOME_CURRENCY: "MXN"},
                SELF_DECLARED,
            ),
            TraceStep(R05, {CREDIT_SCORE: 714}, PREQUALIFIED),
        ),
        facts=(
            fact(INCOME_LOCAL, Decimal(45000), SOURCE_SELF_DECLARED),
            fact(CREDIT_SCORE, 714, SOURCE_SCORE),
        ),
        policy_version="alba-credit-v1",
    )
    assert customer.income_local is None


def test_a_stated_income_of_zero_still_continues_to_the_score() -> None:
    assert decide(profile(credit_score=714, income_local=None), CREDIT_CARD, Decimal(0)) == Decision(
        outcome=PREQUALIFIED,
        deciding_rule=R05,
        rule_trace=(
            TraceStep(R01, {CUSTOMER_STATUS: "Active"}, PASSED),
            TraceStep(R02, {MAX_DAYS_PAST_DUE: 0}, PASSED),
            TraceStep(R03, {MAX_DAYS_PAST_DUE: 0}, PASSED),
            TraceStep(R09, {HOLDS_PRODUCT: False}, PASSED),
            TraceStep(R04, {CREDIT_SCORE: 714}, PASSED),
            TraceStep(
                R06,
                {INCOME_LOCAL: None, DECLARED_INCOME: Decimal(0), INCOME_CURRENCY: "MXN"},
                SELF_DECLARED,
            ),
            TraceStep(R05, {CREDIT_SCORE: 714}, PREQUALIFIED),
        ),
        facts=(
            fact(INCOME_LOCAL, Decimal(0), SOURCE_SELF_DECLARED),
            fact(CREDIT_SCORE, 714, SOURCE_SCORE),
        ),
        policy_version="alba-credit-v1",
    )


def test_a_stated_income_does_not_stop_a_failing_score() -> None:
    assert decide(profile(credit_score=579, income_local=None), CREDIT_CARD, Decimal(45000)) == Decision(
        outcome=NOT_PREQUALIFIED,
        deciding_rule=R05,
        rule_trace=(
            TraceStep(R01, {CUSTOMER_STATUS: "Active"}, PASSED),
            TraceStep(R02, {MAX_DAYS_PAST_DUE: 0}, PASSED),
            TraceStep(R03, {MAX_DAYS_PAST_DUE: 0}, PASSED),
            TraceStep(R09, {HOLDS_PRODUCT: False}, PASSED),
            TraceStep(R04, {CREDIT_SCORE: 579}, PASSED),
            TraceStep(
                R06,
                {INCOME_LOCAL: None, DECLARED_INCOME: Decimal(45000), INCOME_CURRENCY: "MXN"},
                SELF_DECLARED,
            ),
            TraceStep(R05, {CREDIT_SCORE: 579}, NOT_PREQUALIFIED),
        ),
        facts=(
            fact(INCOME_LOCAL, Decimal(45000), SOURCE_SELF_DECLARED),
            fact(CREDIT_SCORE, 579, SOURCE_SCORE),
        ),
        policy_version="alba-credit-v1",
    )


def test_a_file_income_of_zero_is_income() -> None:
    assert decide(profile(credit_score=620, income_local=Decimal(0)), CREDIT_CARD, None) == Decision(
        outcome=PREQUALIFIED,
        deciding_rule=R05,
        rule_trace=(
            TraceStep(R01, {CUSTOMER_STATUS: "Active"}, PASSED),
            TraceStep(R02, {MAX_DAYS_PAST_DUE: 0}, PASSED),
            TraceStep(R03, {MAX_DAYS_PAST_DUE: 0}, PASSED),
            TraceStep(R09, {HOLDS_PRODUCT: False}, PASSED),
            TraceStep(R04, {CREDIT_SCORE: 620}, PASSED),
            TraceStep(
                R06,
                {INCOME_LOCAL: Decimal(0), DECLARED_INCOME: None, INCOME_CURRENCY: "MXN"},
                PASSED,
            ),
            TraceStep(R05, {CREDIT_SCORE: 620}, PREQUALIFIED),
        ),
        facts=(fact(CREDIT_SCORE, 620, SOURCE_SCORE),),
        policy_version="alba-credit-v1",
    )


def test_the_income_on_file_wins_over_a_typed_amount() -> None:
    juan = profile(
        credit_score=812,
        income_local=Decimal("306753.45"),
        income_currency="MXN",
        income_usd=Decimal(17988),
    )
    assert decide(juan, CREDIT_CARD, Decimal(10000)) == Decision(
        outcome=PREQUALIFIED,
        deciding_rule=R05,
        rule_trace=(
            TraceStep(R01, {CUSTOMER_STATUS: "Active"}, PASSED),
            TraceStep(R02, {MAX_DAYS_PAST_DUE: 0}, PASSED),
            TraceStep(R03, {MAX_DAYS_PAST_DUE: 0}, PASSED),
            TraceStep(R09, {HOLDS_PRODUCT: False}, PASSED),
            TraceStep(R04, {CREDIT_SCORE: 812}, PASSED),
            TraceStep(
                R06,
                {INCOME_LOCAL: Decimal("306753.45"), DECLARED_INCOME: Decimal(10000), INCOME_CURRENCY: "MXN"},
                PASSED,
            ),
            TraceStep(R05, {CREDIT_SCORE: 812}, PREQUALIFIED),
        ),
        facts=(fact(CREDIT_SCORE, 812, SOURCE_SCORE),),
        policy_version="alba-credit-v1",
    )


def test_juan_prequalifies_by_r05() -> None:
    juan = profile(
        credit_score=812,
        income_local=Decimal("306753.45"),
        income_currency="MXN",
        income_usd=Decimal(17988),
    )
    assert decide(juan, CREDIT_CARD, None) == Decision(
        outcome=PREQUALIFIED,
        deciding_rule=R05,
        rule_trace=(
            TraceStep(R01, {CUSTOMER_STATUS: "Active"}, PASSED),
            TraceStep(R02, {MAX_DAYS_PAST_DUE: 0}, PASSED),
            TraceStep(R03, {MAX_DAYS_PAST_DUE: 0}, PASSED),
            TraceStep(R09, {HOLDS_PRODUCT: False}, PASSED),
            TraceStep(R04, {CREDIT_SCORE: 812}, PASSED),
            TraceStep(
                R06,
                {INCOME_LOCAL: Decimal("306753.45"), DECLARED_INCOME: None, INCOME_CURRENCY: "MXN"},
                PASSED,
            ),
            TraceStep(R05, {CREDIT_SCORE: 812}, PREQUALIFIED),
        ),
        facts=(fact(CREDIT_SCORE, 812, SOURCE_SCORE),),
        policy_version="alba-credit-v1",
    )


def test_alicia_is_referred_by_r05() -> None:
    alicia = profile(
        credit_score=615,
        income_local=Decimal("4707334.28"),
        income_currency="COP",
        income_usd=Decimal(1167),
    )
    assert decide(alicia, CREDIT_CARD, None) == Decision(
        outcome=REFER,
        deciding_rule=R05,
        rule_trace=(
            TraceStep(R01, {CUSTOMER_STATUS: "Active"}, PASSED),
            TraceStep(R02, {MAX_DAYS_PAST_DUE: 0}, PASSED),
            TraceStep(R03, {MAX_DAYS_PAST_DUE: 0}, PASSED),
            TraceStep(R09, {HOLDS_PRODUCT: False}, PASSED),
            TraceStep(R04, {CREDIT_SCORE: 615}, PASSED),
            TraceStep(
                R06,
                {INCOME_LOCAL: Decimal("4707334.28"), DECLARED_INCOME: None, INCOME_CURRENCY: "COP"},
                PASSED,
            ),
            TraceStep(R05, {CREDIT_SCORE: 615}, REFER),
        ),
        facts=(fact(CREDIT_SCORE, 615, SOURCE_SCORE),),
        policy_version="alba-credit-v1",
    )


def test_mariana_is_decided_by_delinquency_before_her_score() -> None:
    mariana = profile(
        credit_score=515,
        income_local=Decimal("801583.70"),
        income_currency="ARS",
        income_usd=Decimal(2303),
        max_days_past_due=180,
        has_active_card=True,
    )
    assert decide(mariana, PERSONAL_LOAN, None) == Decision(
        outcome=NOT_PREQUALIFIED,
        deciding_rule=R02,
        rule_trace=(
            TraceStep(R01, {CUSTOMER_STATUS: "Active"}, PASSED),
            TraceStep(R02, {MAX_DAYS_PAST_DUE: 180}, NOT_PREQUALIFIED),
        ),
        facts=(fact(MAX_DAYS_PAST_DUE, 180, SOURCE_DAYS),),
        policy_version="alba-credit-v1",
    )


def test_income_usd_does_not_change_the_decision() -> None:
    first = profile(credit_score=812, income_usd=Decimal(17988))
    second = profile(credit_score=812, income_usd=None)
    assert decide(first, CREDIT_CARD, None) == decide(second, CREDIT_CARD, None)


def test_the_same_profile_decides_the_same_way() -> None:
    customer = profile(credit_score=812)
    assert decide(customer, CREDIT_CARD, None) == decide(customer, CREDIT_CARD, None)


def test_declared_income_without_a_currency_is_rejected() -> None:
    with pytest.raises(ValueError, match="income_currency"):
        decide(profile(income_local=None, income_currency=None), CREDIT_CARD, Decimal(45000))


def test_the_score_bands_come_from_the_policy_file(tmp_path: Path) -> None:
    stricter = load_policy(
        policy_file(tmp_path, "  refer_max: 619\n  prequalified_min: 620", "  refer_max: 699\n  prequalified_min: 700")
    )
    assert decide_under(profile(credit_score=650), CREDIT_CARD, None, stricter).rule_trace[-1] == TraceStep(
        R05, {CREDIT_SCORE: 650}, REFER
    )
    assert decide(profile(credit_score=650), CREDIT_CARD, None).rule_trace[-1] == TraceStep(
        R05, {CREDIT_SCORE: 650}, PREQUALIFIED
    )


def test_score_bands_that_leave_a_gap_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="score bands leave a gap between 619 and 621"):
        load_policy(policy_file(tmp_path, "prequalified_min: 620", "prequalified_min: 621"))


def test_delinquency_bands_that_leave_a_gap_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="delinquency bands leave a gap between 29 and 31"):
        load_policy(policy_file(tmp_path, "fail_min: 30", "fail_min: 31"))


def test_a_status_listed_twice_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="customer_status listed twice"):
        load_policy(policy_file(tmp_path, "    - Active", "    - Closed"))


def test_a_status_left_out_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="customer_status must map every status"):
        load_policy(policy_file(tmp_path, "    - Suspended\n", ""))


def test_a_status_the_policy_does_not_know_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="customer_status.passed 'Frozen' is outside the policy"):
        load_policy(policy_file(tmp_path, "    - Active", "    - Frozen"))


def test_a_rule_left_out_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="rules must list every rule"):
        load_policy(policy_file(tmp_path, "  - R09\n", ""))


def test_a_rule_listed_twice_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="rules lists a rule twice"):
        load_policy(policy_file(tmp_path, "  - R09\n", "  - R09\n  - R09\n"))


def test_the_score_band_rule_cannot_run_before_the_empty_score_rule(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="R04 must run before R05"):
        load_policy(policy_file(tmp_path, "  - R04\n  - R06\n  - R05\n", "  - R05\n  - R06\n  - R04\n"))
