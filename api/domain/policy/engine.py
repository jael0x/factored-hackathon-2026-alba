from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType
from typing import Literal, get_args

import yaml

from api.contract_models import (
    IncomeCurrency,
    Outcome,
    PolicyVersion,
    ProductKey,
    RuleId,
    RuleTraceResult,
)
from api.domain.closed_sets import parse_member

CustomerStatus = Literal["Active", "Suspended", "Inactive", "Closed"]

R01: RuleId = "R01"
R02: RuleId = "R02"
R03: RuleId = "R03"
R04: RuleId = "R04"
R05: RuleId = "R05"
R06: RuleId = "R06"
R09: RuleId = "R09"

PREQUALIFIED: Outcome = "PREQUALIFIED"
NOT_PREQUALIFIED: Outcome = "NOT_PREQUALIFIED"
REFER: Outcome = "REFER"
NEEDS_INFO: Outcome = "NEEDS_INFO"
PASSED: RuleTraceResult = "passed"
SELF_DECLARED: RuleTraceResult = "self_declared"

CREDIT_CARD: ProductKey = "credit_card"
PERSONAL_LOAN: ProductKey = "personal_loan"

CUSTOMER_STATUS = "customer_status"
CREDIT_SCORE = "credit_score"
MAX_DAYS_PAST_DUE = "max_days_past_due"
HOLDS_PRODUCT = "holds_product"
INCOME_LOCAL = "income_local"
DECLARED_INCOME = "declared_income"
INCOME_CURRENCY = "income_currency"
INCOME_USD = "income_usd"

SOURCE_STATUS = "customer_credit_profile.customer_status"
SOURCE_SCORE = "customer_credit_profile.credit_score"
SOURCE_DAYS = "customer_credit_profile.max_days_past_due"
SOURCE_INCOME = "customer_credit_profile.income_local"
SOURCE_CURRENCY = "customer_credit_profile.income_currency"
SOURCE_INCOME_USD = "customer_credit_profile.income_usd"
SOURCE_PRODUCTS = "products"
SOURCE_SELF_DECLARED = "self_declared"

CUSTOMER_STATUSES: frozenset[CustomerStatus] = frozenset(get_args(CustomerStatus))
RULE_IDS: frozenset[RuleId] = frozenset(get_args(RuleId))
POLICY_VERSIONS: frozenset[PolicyVersion] = frozenset(get_args(PolicyVersion))

POLICY_PATH = Path(__file__).with_name("alba-credit-v1.yaml")

TraceValue = Decimal | int | str | bool | None


def parse_customer_status(value: object) -> CustomerStatus:
    return parse_member(value, CUSTOMER_STATUSES, CUSTOMER_STATUS)


def require_adjacent(low_max: int, next_min: int, label: str) -> None:
    if low_max + 1 != next_min:
        raise ValueError(f"{label} bands leave a gap between {low_max} and {next_min}")


@dataclass(frozen=True)
class CreditProfile:
    customer_status: CustomerStatus
    credit_score: int | None
    income_local: Decimal | None
    income_currency: IncomeCurrency | None
    income_usd: Decimal | None
    max_days_past_due: int
    has_active_card: bool
    has_active_personal_loan: bool
    as_of: date

    def __post_init__(self) -> None:
        parse_customer_status(self.customer_status)


@dataclass(frozen=True)
class PolicyFact:
    name: str
    value: TraceValue
    source: str
    as_of: date


@dataclass(frozen=True)
class TraceStep:
    rule_id: RuleId
    input: dict[str, TraceValue]
    result: RuleTraceResult


@dataclass(frozen=True)
class Decision:
    outcome: Outcome
    deciding_rule: RuleId
    rule_trace: tuple[TraceStep, ...]
    facts: tuple[PolicyFact, ...]
    policy_version: PolicyVersion


@dataclass(frozen=True)
class ScoreBands:
    refer_min: int
    refer_max: int
    prequalified_min: int

    def __post_init__(self) -> None:
        if self.refer_min > self.refer_max:
            raise ValueError("score refer_min is above refer_max")
        require_adjacent(self.refer_max, self.prequalified_min, "score")

    def result_for(self, score: int) -> RuleTraceResult:
        if score < self.refer_min:
            return NOT_PREQUALIFIED
        if score <= self.refer_max:
            return REFER
        return PREQUALIFIED


@dataclass(frozen=True)
class DelinquencyBands:
    refer_min: int
    refer_max: int
    fail_min: int

    def __post_init__(self) -> None:
        if self.refer_min > self.refer_max:
            raise ValueError("delinquency refer_min is above refer_max")
        require_adjacent(self.refer_max, self.fail_min, "delinquency")


@dataclass(frozen=True)
class StatusRules:
    refer: frozenset[CustomerStatus]
    not_prequalified: frozenset[CustomerStatus]
    passed: frozenset[CustomerStatus]

    def __post_init__(self) -> None:
        listed = [status for group in (self.refer, self.not_prequalified, self.passed) for status in group]
        if len(listed) != len(set(listed)):
            raise ValueError("customer_status listed twice")
        if set(listed) != CUSTOMER_STATUSES:
            raise ValueError(f"customer_status must map every status: {sorted(CUSTOMER_STATUSES)}")

    def result_for(self, status: CustomerStatus) -> RuleTraceResult:
        if status in self.refer:
            return REFER
        if status in self.not_prequalified:
            return NOT_PREQUALIFIED
        return PASSED


@dataclass(frozen=True)
class PolicySpec:
    version: PolicyVersion
    rules: tuple[RuleId, ...]
    status: StatusRules
    score: ScoreBands
    delinquency: DelinquencyBands

    def __post_init__(self) -> None:
        require_rule_order(self.rules)


@dataclass(frozen=True)
class RuleEvaluation:
    step: TraceStep
    deciding_fact: PolicyFact | None = None
    declared_income_fact: PolicyFact | None = None


RuleApply = Callable[[CreditProfile, ProductKey, Decimal | None, PolicySpec], RuleEvaluation]


def holds_card(profile: CreditProfile) -> bool:
    return profile.has_active_card


def holds_personal_loan(profile: CreditProfile) -> bool:
    return profile.has_active_personal_loan


HOLDS_BY_PRODUCT: Mapping[ProductKey, Callable[[CreditProfile], bool]] = MappingProxyType(
    {CREDIT_CARD: holds_card, PERSONAL_LOAN: holds_personal_loan}
)


def parse_product(value: object) -> ProductKey:
    return parse_member(value, frozenset(HOLDS_BY_PRODUCT), "product")


def parse_declared_income(value: object) -> Decimal | None:
    if value is None:
        return None
    if type(value) is not Decimal:
        raise TypeError("declared_income must be Decimal or None")
    if not value.is_finite():
        raise ValueError("declared_income must be a finite amount")
    if value < 0:
        raise ValueError("declared_income must not be negative")
    return value


def require_declared_currency(profile: CreditProfile, declared_income: Decimal | None) -> None:
    if declared_income is not None and profile.income_currency is None:
        raise ValueError("declared income requires income_currency")


def is_terminal(result: RuleTraceResult) -> bool:
    return result != PASSED and result != SELF_DECLARED


def terminal_step(steps: Sequence[TraceStep]) -> TraceStep:
    for step in steps:
        if is_terminal(step.result):
            return step
    raise ValueError("policy produced no terminal rule")


def outcome_of(result: RuleTraceResult) -> Outcome:
    if result == PREQUALIFIED:
        return PREQUALIFIED
    if result == NOT_PREQUALIFIED:
        return NOT_PREQUALIFIED
    if result == REFER:
        return REFER
    if result == NEEDS_INFO:
        return NEEDS_INFO
    raise ValueError(f"result {result!r} is not terminal")


def _step(rule_id: RuleId, result: RuleTraceResult, fields: Mapping[str, TraceValue]) -> TraceStep:
    return TraceStep(rule_id=rule_id, input=dict(fields), result=result)


def _fact(name: str, value: TraceValue, source: str, as_of: date) -> PolicyFact:
    return PolicyFact(name=name, value=value, source=source, as_of=as_of)


def apply_r01(
    profile: CreditProfile,
    _product: ProductKey,
    _declared_income: Decimal | None,
    spec: PolicySpec,
) -> RuleEvaluation:
    status = profile.customer_status
    step = _step(R01, spec.status.result_for(status), {CUSTOMER_STATUS: status})
    if step.result == PASSED:
        return RuleEvaluation(step)
    return RuleEvaluation(step, deciding_fact=_fact(CUSTOMER_STATUS, status, SOURCE_STATUS, profile.as_of))


def apply_r02(
    profile: CreditProfile,
    _product: ProductKey,
    _declared_income: Decimal | None,
    spec: PolicySpec,
) -> RuleEvaluation:
    days = profile.max_days_past_due
    fields = {MAX_DAYS_PAST_DUE: days}
    if days >= spec.delinquency.fail_min:
        return RuleEvaluation(
            _step(R02, NOT_PREQUALIFIED, fields),
            deciding_fact=_fact(MAX_DAYS_PAST_DUE, days, SOURCE_DAYS, profile.as_of),
        )
    return RuleEvaluation(_step(R02, PASSED, fields))


def apply_r03(
    profile: CreditProfile,
    _product: ProductKey,
    _declared_income: Decimal | None,
    spec: PolicySpec,
) -> RuleEvaluation:
    days = profile.max_days_past_due
    fields = {MAX_DAYS_PAST_DUE: days}
    if spec.delinquency.refer_min <= days <= spec.delinquency.refer_max:
        return RuleEvaluation(
            _step(R03, REFER, fields),
            deciding_fact=_fact(MAX_DAYS_PAST_DUE, days, SOURCE_DAYS, profile.as_of),
        )
    return RuleEvaluation(_step(R03, PASSED, fields))


def apply_r09(
    profile: CreditProfile,
    product: ProductKey,
    _declared_income: Decimal | None,
    _spec: PolicySpec,
) -> RuleEvaluation:
    held = HOLDS_BY_PRODUCT[product](profile)
    fields = {HOLDS_PRODUCT: held}
    if held:
        return RuleEvaluation(
            _step(R09, REFER, fields),
            deciding_fact=_fact(HOLDS_PRODUCT, True, SOURCE_PRODUCTS, profile.as_of),
        )
    return RuleEvaluation(_step(R09, PASSED, fields))


def apply_r04(
    profile: CreditProfile,
    _product: ProductKey,
    _declared_income: Decimal | None,
    _spec: PolicySpec,
) -> RuleEvaluation:
    score = profile.credit_score
    fields = {CREDIT_SCORE: score}
    if score is None:
        return RuleEvaluation(
            _step(R04, REFER, fields),
            deciding_fact=_fact(CREDIT_SCORE, None, SOURCE_SCORE, profile.as_of),
        )
    return RuleEvaluation(_step(R04, PASSED, fields))


def apply_r06(
    profile: CreditProfile,
    _product: ProductKey,
    declared_income: Decimal | None,
    _spec: PolicySpec,
) -> RuleEvaluation:
    fields = {
        INCOME_LOCAL: profile.income_local,
        DECLARED_INCOME: declared_income,
        INCOME_CURRENCY: profile.income_currency,
    }
    if profile.income_local is not None:
        return RuleEvaluation(_step(R06, PASSED, fields))
    if declared_income is None:
        return RuleEvaluation(
            _step(R06, NEEDS_INFO, fields),
            deciding_fact=_fact(INCOME_LOCAL, None, SOURCE_INCOME, profile.as_of),
        )
    return RuleEvaluation(
        _step(R06, SELF_DECLARED, fields),
        declared_income_fact=_fact(INCOME_LOCAL, declared_income, SOURCE_SELF_DECLARED, profile.as_of),
    )


def apply_r05(
    profile: CreditProfile,
    _product: ProductKey,
    _declared_income: Decimal | None,
    spec: PolicySpec,
) -> RuleEvaluation:
    score = profile.credit_score
    if score is None:
        raise ValueError("R05 requires a credit_score; R04 closes on an empty one first")
    return RuleEvaluation(
        _step(R05, spec.score.result_for(score), {CREDIT_SCORE: score}),
        deciding_fact=_fact(CREDIT_SCORE, score, SOURCE_SCORE, profile.as_of),
    )


RULES: Mapping[RuleId, RuleApply] = MappingProxyType(
    {
        R01: apply_r01,
        R02: apply_r02,
        R03: apply_r03,
        R09: apply_r09,
        R04: apply_r04,
        R06: apply_r06,
        R05: apply_r05,
    }
)

RUNS_AFTER: Mapping[RuleId, RuleId] = MappingProxyType({R05: R04})


def require_rule_order(rules: tuple[RuleId, ...]) -> None:
    if len(rules) != len(set(rules)):
        raise ValueError("rules lists a rule twice")
    if set(rules) != RULE_IDS:
        raise ValueError(f"rules must list every rule: {sorted(RULE_IDS)}")
    unimplemented = RULE_IDS - set(RULES)
    if unimplemented:
        raise ValueError(f"no implementation for {sorted(unimplemented)}")
    for rule_id, earlier in RUNS_AFTER.items():
        if rules.index(earlier) > rules.index(rule_id):
            raise ValueError(f"{earlier} must run before {rule_id}")


def evaluate(
    profile: CreditProfile,
    product: ProductKey,
    declared_income: Decimal | None,
    spec: PolicySpec,
) -> tuple[RuleEvaluation, ...]:
    found: list[RuleEvaluation] = []
    for rule_id in spec.rules:
        evaluation = RULES[rule_id](profile, product, declared_income, spec)
        found.append(evaluation)
        if is_terminal(evaluation.step.result):
            return tuple(found)
    return tuple(found)


def cited_facts(profile: CreditProfile, declared_income: PolicyFact | None) -> tuple[PolicyFact, ...]:
    file_income = _fact(INCOME_LOCAL, profile.income_local, SOURCE_INCOME, profile.as_of)
    return (
        _fact(CREDIT_SCORE, profile.credit_score, SOURCE_SCORE, profile.as_of),
        file_income if declared_income is None else declared_income,
        _fact(INCOME_CURRENCY, profile.income_currency, SOURCE_CURRENCY, profile.as_of),
        _fact(INCOME_USD, profile.income_usd, SOURCE_INCOME_USD, profile.as_of),
    )


def decision_from(evaluations: tuple[RuleEvaluation, ...], profile: CreditProfile, spec: PolicySpec) -> Decision:
    winner = terminal_step(tuple(evaluation.step for evaluation in evaluations))
    closing = next(evaluation.deciding_fact for evaluation in evaluations if evaluation.step.rule_id == winner.rule_id)
    if closing is None:
        raise ValueError(f"{winner.rule_id} closed without a fact")
    declared = next(
        (evaluation.declared_income_fact for evaluation in evaluations if evaluation.declared_income_fact is not None),
        None,
    )
    cited = tuple(fact for fact in cited_facts(profile, declared) if fact.name != closing.name)
    return Decision(
        outcome=outcome_of(winner.result),
        deciding_rule=winner.rule_id,
        rule_trace=tuple(evaluation.step for evaluation in evaluations),
        facts=(closing, *cited),
        policy_version=spec.version,
    )


def decide_under(
    profile: CreditProfile,
    product: ProductKey,
    declared_income: Decimal | None,
    spec: PolicySpec,
) -> Decision:
    product_key = parse_product(product)
    amount = parse_declared_income(declared_income)
    require_declared_currency(profile, amount)
    return decision_from(evaluate(profile, product_key, amount, spec), profile, spec)


def decide(profile: CreditProfile, product: ProductKey, declared_income: Decimal | None) -> Decision:
    return decide_under(profile, product, declared_income, ALBA_CREDIT_V1)


def load_policy(path: Path = POLICY_PATH) -> PolicySpec:
    document = require_mapping(yaml.safe_load(path.read_text(encoding="utf-8")), "policy")
    require_keys(
        document,
        frozenset({"policy_version", "rules", "customer_status", "score", "delinquency"}),
        "policy",
    )
    return PolicySpec(
        version=parse_member(document["policy_version"], POLICY_VERSIONS, "policy_version"),
        rules=parse_rules(document["rules"]),
        status=parse_status(document["customer_status"]),
        score=parse_score(document["score"]),
        delinquency=parse_delinquency(document["delinquency"]),
    )


def require_mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be a mapping")
    parsed: dict[str, object] = {}
    for key, item in value.items():
        if type(key) is not str:
            raise TypeError(f"{label} keys must be strings")
        parsed[key] = item
    return parsed


def require_keys(mapping: dict[str, object], keys: frozenset[str], label: str) -> None:
    if set(mapping) != keys:
        raise ValueError(f"{label} keys must be {sorted(keys)}")


def require_int(value: object, label: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{label} must be an integer")
    return value


def require_list(value: object, label: str) -> list[object]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} must be a non-empty list")
    return list(value)


def parse_rules(value: object) -> tuple[RuleId, ...]:
    return tuple(parse_member(item, RULE_IDS, "rule") for item in require_list(value, "rules"))


def parse_statuses(value: object, label: str) -> frozenset[CustomerStatus]:
    parsed = [parse_member(item, CUSTOMER_STATUSES, label) for item in require_list(value, label)]
    if len(parsed) != len(set(parsed)):
        raise ValueError(f"{label} listed twice")
    return frozenset(parsed)


def parse_status(value: object) -> StatusRules:
    mapping = require_mapping(value, CUSTOMER_STATUS)
    require_keys(mapping, frozenset({"refer", "not_prequalified", "passed"}), CUSTOMER_STATUS)
    return StatusRules(
        refer=parse_statuses(mapping["refer"], "customer_status.refer"),
        not_prequalified=parse_statuses(mapping["not_prequalified"], "customer_status.not_prequalified"),
        passed=parse_statuses(mapping["passed"], "customer_status.passed"),
    )


def parse_score(value: object) -> ScoreBands:
    mapping = require_mapping(value, "score")
    require_keys(mapping, frozenset({"refer_min", "refer_max", "prequalified_min"}), "score")
    return ScoreBands(
        refer_min=require_int(mapping["refer_min"], "score.refer_min"),
        refer_max=require_int(mapping["refer_max"], "score.refer_max"),
        prequalified_min=require_int(mapping["prequalified_min"], "score.prequalified_min"),
    )


def parse_delinquency(value: object) -> DelinquencyBands:
    mapping = require_mapping(value, "delinquency")
    require_keys(mapping, frozenset({"refer_min", "refer_max", "fail_min"}), "delinquency")
    return DelinquencyBands(
        refer_min=require_int(mapping["refer_min"], "delinquency.refer_min"),
        refer_max=require_int(mapping["refer_max"], "delinquency.refer_max"),
        fail_min=require_int(mapping["fail_min"], "delinquency.fail_min"),
    )


ALBA_CREDIT_V1 = load_policy()
