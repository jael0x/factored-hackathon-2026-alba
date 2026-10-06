from dataclasses import dataclass
from uuid import UUID

from api.contract_models import Locale, Outcome, PolicyVersion, ProcessState, ProductKey, ReasonCode, RuleId
from api.domain.closed_sets import parse_member
from api.domain.policy.engine import CREDIT_SCORE, NEEDS_INFO, RULE_IDS
from api.domain.process.case import IncomeFacts, facts_by_name, income_facts
from api.domain.process.lifecycle import REASON_CODES
from api.domain.process.stored_events import Payload, field, parse_analysis


@dataclass(frozen=True)
class StoredEvent:
    event_id: UUID
    payload: Payload


# A case as the consultant reads it: its latest analysis and its latest thread_taken, each by seq.
@dataclass(frozen=True)
class HandoffSource:
    process_id: UUID
    customer_id: str
    first_name: str
    last_name: str
    state: ProcessState
    locale: Locale
    analysis: StoredEvent | None
    thread_taken: StoredEvent | None


@dataclass(frozen=True)
class QueueItem:
    process_id: UUID
    customer_id: str
    first_name: str
    last_name: str
    product: ProductKey | None
    reason_code: ReasonCode
    locale: Locale


@dataclass(frozen=True)
class PolicyResult:
    product: ProductKey
    credit_score: int | None
    income: IncomeFacts
    deciding_rule: RuleId
    policy_version: PolicyVersion
    outcome: Outcome


@dataclass(frozen=True)
class HandoffPacket:
    process_id: UUID
    customer_id: str
    first_name: str
    last_name: str
    locale: Locale
    reason_code: ReasonCode
    result: PolicyResult | None
    closable: bool


def packet_of(source: HandoffSource) -> HandoffPacket:
    result = None if source.analysis is None else policy_result(source.analysis)
    return HandoffPacket(
        process_id=source.process_id,
        customer_id=source.customer_id,
        first_name=source.first_name,
        last_name=source.last_name,
        locale=source.locale,
        reason_code=handoff_reason(source.process_id, source.thread_taken),
        result=result,
        closable=is_closable(result),
    )


def policy_result(analysis: StoredEvent) -> PolicyResult:
    parsed = parse_analysis(analysis.event_id, analysis.payload)
    facts = field(analysis.payload, "facts")
    return PolicyResult(
        product=parsed.product,
        credit_score=cited_score(facts),
        income=income_facts(facts),
        deciding_rule=parse_member(field(analysis.payload, "deciding_rule"), RULE_IDS, "deciding_rule"),
        policy_version=parsed.policy_version,
        outcome=parsed.outcome,
    )


# A person closes only a case the policy reached a result for (PLAN.md D15 (3)).
def is_closable(result: PolicyResult | None) -> bool:
    return result is not None and result.outcome != NEEDS_INFO


def handoff_reason(process_id: UUID, thread_taken: StoredEvent | None) -> ReasonCode:
    if thread_taken is None:
        raise ValueError(f"process {process_id} is with a person but no conversation.thread_taken says why")
    return parse_member(field(thread_taken.payload, "reason_code"), REASON_CODES, "reason_code")


def cited_score(facts: object) -> int | None:
    cited = facts_by_name(facts)
    if CREDIT_SCORE not in cited:
        raise ValueError(f"the analysis does not cite {CREDIT_SCORE}")
    score = field(cited[CREDIT_SCORE], "value")
    if score is not None and type(score) is not int:
        raise TypeError(f"{CREDIT_SCORE} must be a whole number or empty, got {score!r}")
    return score
