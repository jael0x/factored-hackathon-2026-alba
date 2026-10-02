from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import get_args

import yaml

from api.contract_models import IncomeCurrency, Outcome, PolicyVersion, ProductKey, RuleId, RuleTraceResult

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

SOURCE_STATUS = "customer_credit_profile.customer_status"
SOURCE_SCORE = "customer_credit_profile.credit_score"
SOURCE_DAYS = "customer_credit_profile.max_days_past_due"
SOURCE_INCOME = "customer_credit_profile.income_local"
SOURCE_PRODUCTS = "products"
SOURCE_SELF_DECLARED = "self_declared"

POLICY_PATH = Path(__file__).with_name("alba-credit-v1.yaml")

TraceValue = Decimal | int | str | bool | None


@dataclass(frozen=True)
class CreditProfile:
    customer_status: str
    credit_score: int | None
    income_local: Decimal | None
    income_currency: IncomeCurrency | None
    income_usd: Decimal | None
    max_days_past_due: int
    has_active_card: bool
    has_active_personal_loan: bool
    as_of: date


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


@dataclass(frozen=True)
class DelinquencyBands:
    refer_min: int
    refer_max: int
    fail_min: int


@dataclass(frozen=True)
class StatusRules:
    refer: frozenset[str]
    not_prequalified: frozenset[str]
    passed: frozenset[str]


@dataclass(frozen=True)
class PolicySpec:
    version: PolicyVersion
    rules: tuple[RuleId, ...]
    status: StatusRules
    score: ScoreBands
    delinquency: DelinquencyBands


@dataclass(frozen=True)
class RuleEvaluation:
    step: TraceStep
    deciding_fact: PolicyFact | None = None
    declared_income_fact: PolicyFact | None = None


RuleApply = Callable[[CreditProfile, ProductKey, Decimal | None, PolicySpec], RuleEvaluation]


def declared_amount(value: object) -> Decimal | None:
    if value is None:
        return None
    if type(value) is not Decimal:
        raise ValueError("declared_income must be Decimal or None")
    return value


def known_statuses(status: StatusRules) -> frozenset[str]:
    return status.refer | status.not_prequalified | status.passed


def is_terminal(result: RuleTraceResult) -> bool:
    return result != PASSED and result != SELF_DECLARED


def terminal_step(steps: Sequence[TraceStep]) -> TraceStep:
    for step in steps:
        if is_terminal(step.result):
            return step
    raise ValueError("policy produced no terminal rule")


def holds_product(profile: CreditProfile, product: ProductKey) -> bool:
    if product == CREDIT_CARD:
        return profile.has_active_card
    if product == PERSONAL_LOAN:
        return profile.has_active_personal_loan
    raise ValueError(f"unknown product {product!r}")


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


def _step(rule_id: RuleId, result: RuleTraceResult, fields: dict[str, TraceValue]) -> TraceStep:
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
    fields = {CUSTOMER_STATUS: status}
    if status in spec.status.refer:
        return RuleEvaluation(
            _step(R01, REFER, fields),
            deciding_fact=_fact(CUSTOMER_STATUS, status, SOURCE_STATUS, profile.as_of),
        )
    if status in spec.status.not_prequalified:
        return RuleEvaluation(
            _step(R01, NOT_PREQUALIFIED, fields),
            deciding_fact=_fact(CUSTOMER_STATUS, status, SOURCE_STATUS, profile.as_of),
        )
    if status in spec.status.passed:
        return RuleEvaluation(_step(R01, PASSED, fields))
    raise ValueError(f"customer_status {status!r} is outside the policy")


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
    held = holds_product(profile, product)
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
        raise ValueError("R05 requires a credit_score")
    if score < spec.score.refer_min:
        result: RuleTraceResult = NOT_PREQUALIFIED
    elif score <= spec.score.refer_max:
        result = REFER
    else:
        result = PREQUALIFIED
    return RuleEvaluation(
        _step(R05, result, {CREDIT_SCORE: score}),
        deciding_fact=_fact(CREDIT_SCORE, score, SOURCE_SCORE, profile.as_of),
    )


RULES: dict[RuleId, RuleApply] = {
    R01: apply_r01,
    R02: apply_r02,
    R03: apply_r03,
    R09: apply_r09,
    R04: apply_r04,
    R06: apply_r06,
    R05: apply_r05,
}


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


def decide(profile: CreditProfile, product: ProductKey, declared_income: Decimal | None) -> Decision:
    amount = declared_amount(declared_income)
    require_product(product)
    require_known_status(profile, _POLICY)
    require_declared_currency(profile, amount)
    evaluations = evaluate(profile, product, amount, _POLICY)
    winner = terminal_step(tuple(evaluation.step for evaluation in evaluations))
    declared_fact = next(
        (evaluation.declared_income_fact for evaluation in evaluations if evaluation.declared_income_fact is not None),
        None,
    )
    closing = next(evaluation.deciding_fact for evaluation in evaluations if evaluation.step.rule_id == winner.rule_id)
    if closing is None:
        raise ValueError(f"{winner.rule_id} closed without a fact")
    facts = (declared_fact, closing) if declared_fact is not None else (closing,)
    return Decision(
        outcome=outcome_of(winner.result),
        deciding_rule=winner.rule_id,
        rule_trace=tuple(evaluation.step for evaluation in evaluations),
        facts=facts,
        policy_version=_POLICY.version,
    )


def require_product(product: ProductKey) -> None:
    for known in get_args(ProductKey):
        if product == known:
            return
    raise ValueError(f"unknown product {product!r}")


def require_known_status(profile: CreditProfile, spec: PolicySpec) -> None:
    if profile.customer_status not in known_statuses(spec.status):
        raise ValueError(f"customer_status {profile.customer_status!r} is outside the policy")


def require_declared_currency(profile: CreditProfile, declared_income: Decimal | None) -> None:
    if declared_income is not None and profile.income_currency is None:
        raise ValueError("declared income requires income_currency")


def load_policy(path: Path = POLICY_PATH) -> PolicySpec:
    document = require_mapping(yaml.safe_load(path.read_text(encoding="utf-8")), "policy")
    require_keys(
        document,
        frozenset({"policy_version", "rules", "customer_status", "score", "delinquency"}),
        "policy",
    )
    rules = require_rules(document["rules"])
    missing = [rule_id for rule_id in rules if rule_id not in RULES]
    if missing:
        raise ValueError(f"no implementation for {missing}")
    return PolicySpec(
        version=parse_version(document["policy_version"]),
        rules=rules,
        status=parse_status(document["customer_status"]),
        score=parse_score(document["score"]),
        delinquency=parse_delinquency(document["delinquency"]),
    )


def require_mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a mapping")
    parsed: dict[str, object] = {}
    for key, item in value.items():
        if type(key) is not str:
            raise ValueError(f"{label} keys must be strings")
        parsed[key] = item
    return parsed


def require_keys(mapping: dict[str, object], keys: frozenset[str], label: str) -> None:
    if set(mapping) != keys:
        raise ValueError(f"{label} keys must be {sorted(keys)}")


def require_int(value: object, label: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{label} must be an integer")
    return value


def require_next(low_max: int, next_min: int, label: str) -> None:
    if low_max + 1 != next_min:
        raise ValueError(f"{label} bands leave a gap between {low_max} and {next_min}")


def require_strings(value: object, label: str) -> frozenset[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} must be a list of strings")
    parsed: list[str] = []
    for item in value:
        if type(item) is not str:
            raise ValueError(f"{label} must be a list of strings")
        parsed.append(item)
    return frozenset(parsed)


def require_disjoint(groups: tuple[frozenset[str], ...], label: str) -> None:
    seen: set[str] = set()
    for group in groups:
        overlap = seen & group
        if overlap:
            raise ValueError(f"{label} listed twice: {sorted(overlap)}")
        seen.update(group)


def parse_version(value: object) -> PolicyVersion:
    for version in get_args(PolicyVersion):
        if value == version:
            return version
    raise ValueError(f"policy_version {value!r} is outside the policy")


def parse_rule_id(value: object) -> RuleId:
    for rule_id in get_args(RuleId):
        if value == rule_id:
            return rule_id
    raise ValueError(f"unknown rule {value!r}")


def require_rules(value: object) -> tuple[RuleId, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError("rules must be a list")
    parsed = tuple(parse_rule_id(item) for item in value)
    if len(parsed) != len(set(parsed)):
        raise ValueError("rules lists a rule twice")
    return parsed


def parse_status(value: object) -> StatusRules:
    mapping = require_mapping(value, "customer_status")
    require_keys(mapping, frozenset({"refer", "not_prequalified", "passed"}), "customer_status")
    status = StatusRules(
        refer=require_strings(mapping["refer"], "customer_status.refer"),
        not_prequalified=require_strings(mapping["not_prequalified"], "customer_status.not_prequalified"),
        passed=require_strings(mapping["passed"], "customer_status.passed"),
    )
    require_disjoint((status.refer, status.not_prequalified, status.passed), "customer_status")
    return status


def parse_score(value: object) -> ScoreBands:
    mapping = require_mapping(value, "score")
    require_keys(mapping, frozenset({"refer_min", "refer_max", "prequalified_min"}), "score")
    bands = ScoreBands(
        refer_min=require_int(mapping["refer_min"], "score.refer_min"),
        refer_max=require_int(mapping["refer_max"], "score.refer_max"),
        prequalified_min=require_int(mapping["prequalified_min"], "score.prequalified_min"),
    )
    if bands.refer_min > bands.refer_max:
        raise ValueError("score refer_min is above refer_max")
    require_next(bands.refer_max, bands.prequalified_min, "score")
    return bands


def parse_delinquency(value: object) -> DelinquencyBands:
    mapping = require_mapping(value, "delinquency")
    require_keys(mapping, frozenset({"refer_min", "refer_max", "fail_min"}), "delinquency")
    bands = DelinquencyBands(
        refer_min=require_int(mapping["refer_min"], "delinquency.refer_min"),
        refer_max=require_int(mapping["refer_max"], "delinquency.refer_max"),
        fail_min=require_int(mapping["fail_min"], "delinquency.fail_min"),
    )
    if bands.refer_min > bands.refer_max:
        raise ValueError("delinquency refer_min is above refer_max")
    require_next(bands.refer_max, bands.fail_min, "delinquency")
    return bands


_POLICY = load_policy()
