from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from api.contract_models import Outcome, ReasonCode
from api.domain.policy.engine import CreditProfile, decide
from api.domain.process.case import NO_INCOME_FACTS, IncomeFacts
from api.domain.process.events import transition_key
from api.domain.process.lifecycle import ProcessRow
from api.domain.process.new_events import Cause, analysis_completed, thread_taken
from api.domain.process.packet import (
    HandoffPacket,
    HandoffSource,
    PolicyResult,
    StoredEvent,
    handoff_reason,
    is_closable,
    packet_of,
)
from api.domain.process.stored_events import Payload

PROCESS_ID = UUID("11111111-1111-4111-8111-111111111111")
ANALYSIS_ID = UUID("22222222-2222-4222-8222-222222222222")
TAKEN_ID = UUID("33333333-3333-4333-8333-333333333333")
CAUSE = Cause(event_id=UUID("44444444-4444-4444-8444-444444444444"), command_id=None)
ALICIA = "CLI-440CO5FZIY6A"
AS_OF = date(2026, 6, 17)
CASE = ProcessRow(process_id=PROCESS_ID, customer_id=ALICIA, state="ai_active")


def profile(score: int | None, income: Decimal | None) -> CreditProfile:
    return CreditProfile(
        customer_status="Active",
        credit_score=score,
        income_local=income,
        income_currency="COP",
        income_usd=None if income is None else Decimal("1167.42"),
        max_days_past_due=0,
        has_active_card=False,
        has_active_personal_loan=False,
        as_of=AS_OF,
    )


ALICIA_PROFILE = profile(615, Decimal("4707334.28"))


def analysis(credit: CreditProfile = ALICIA_PROFILE) -> StoredEvent:
    event = analysis_completed(CASE, decide(credit, "credit_card", None), "credit_card", "pt", CAUSE)
    return StoredEvent(ANALYSIS_ID, event.payload)


def taken(reason: ReasonCode) -> StoredEvent:
    return StoredEvent(
        TAKEN_ID, thread_taken(CASE, reason, transition_key(PROCESS_ID, "human_active", CAUSE.event_id), CAUSE).payload
    )


def source(analysis: StoredEvent | None, thread: StoredEvent | None) -> HandoffSource:
    return HandoffSource(
        process_id=PROCESS_ID,
        customer_id=ALICIA,
        first_name="Alicia Mariana",
        last_name="Parra Álvarez",
        state="human_active",
        locale="pt",
        analysis=analysis,
        thread_taken=thread,
    )


def result(outcome: Outcome) -> PolicyResult:
    return PolicyResult("credit_card", 615, NO_INCOME_FACTS, "R05", "alba-credit-v1", outcome)


def test_a_referred_case_carries_the_analysis_and_may_be_closed() -> None:
    assert packet_of(source(analysis(), taken("policy_refer"))) == HandoffPacket(
        process_id=PROCESS_ID,
        customer_id=ALICIA,
        first_name="Alicia Mariana",
        last_name="Parra Álvarez",
        locale="pt",
        reason_code="policy_refer",
        result=PolicyResult(
            product="credit_card",
            credit_score=615,
            income=IncomeFacts(Decimal("4707334.28"), "COP", Decimal("1167.42"), AS_OF),
            deciding_rule="R05",
            policy_version="alba-credit-v1",
            outcome="REFER",
        ),
        closable=True,
    )


def test_a_case_left_at_needs_info_shows_no_income_and_may_not_be_closed() -> None:
    packet = packet_of(source(analysis(profile(714, None)), taken("customer_requested_human")))
    assert (packet.reason_code, packet.result, packet.closable) == (
        "customer_requested_human",
        PolicyResult("credit_card", 714, IncomeFacts(None, "COP", None, AS_OF), "R06", "alba-credit-v1", "NEEDS_INFO"),
        False,
    )


def test_a_case_handed_off_before_the_policy_ran_has_no_result_and_may_not_be_closed() -> None:
    packet = packet_of(source(None, taken("tool_failed")))
    assert (packet.reason_code, packet.result, packet.closable) == ("tool_failed", None, False)


def test_an_empty_score_stays_empty() -> None:
    packet = packet_of(source(analysis(profile(None, Decimal("4707334.28"))), taken("policy_refer")))
    assert packet.result is not None
    assert (packet.result.credit_score, packet.result.outcome, packet.result.deciding_rule) == (None, "REFER", "R04")


@pytest.mark.parametrize(
    ("outcome", "closable"),
    [("PREQUALIFIED", True), ("NOT_PREQUALIFIED", True), ("REFER", True), ("NEEDS_INFO", False)],
)
def test_only_a_result_the_policy_reached_may_be_closed(outcome: Outcome, closable: bool) -> None:
    assert is_closable(result(outcome)) is closable


def test_no_analysis_may_not_be_closed() -> None:
    assert is_closable(None) is False


def test_a_case_with_a_person_and_no_thread_taken_fails_loud() -> None:
    with pytest.raises(ValueError, match=f"process {PROCESS_ID} is with a person but no"):
        handoff_reason(PROCESS_ID, None)


def test_a_reason_outside_the_closed_list_fails_loud() -> None:
    with pytest.raises(ValueError, match="reason_code 'policy_r05'"):
        handoff_reason(PROCESS_ID, StoredEvent(TAKEN_ID, {"reason_code": "policy_r05"}))


def without_score(payload: Payload) -> Payload:
    facts = payload["facts"]
    assert isinstance(facts, list)
    return {**payload, "facts": [fact for fact in facts if fact["name"] != "credit_score"]}


def with_score(payload: Payload, score: object) -> Payload:
    facts = payload["facts"]
    assert isinstance(facts, list)
    return {
        **payload,
        "facts": [{**fact, "value": score} if fact["name"] == "credit_score" else fact for fact in facts],
    }


def test_an_analysis_that_does_not_cite_the_score_fails_loud() -> None:
    stored = analysis()
    with pytest.raises(ValueError, match="the analysis does not cite credit_score"):
        packet_of(source(StoredEvent(ANALYSIS_ID, without_score(stored.payload)), taken("policy_refer")))


@pytest.mark.parametrize("score", [Decimal("615.5"), True, "615"])
def test_a_score_that_is_not_a_whole_number_fails_loud(score: object) -> None:
    stored = analysis()
    with pytest.raises(TypeError, match="credit_score must be a whole number or empty"):
        packet_of(source(StoredEvent(ANALYSIS_ID, with_score(stored.payload, score)), taken("policy_refer")))
