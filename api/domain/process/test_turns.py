from uuid import UUID, uuid4

import pytest

from api.contract_models import Intent, Outcome, ProductKey, TemplateId, TurnLanguage
from api.domain.process.stored_events import AnalysisCompleted, ShownTurn, StoredEvent, TemplateSent, WithheldTurn
from api.domain.process.turns import TurnStamp, stamp_turn

EVENT_ID = UUID("77777777-7777-4777-8777-777777777777")


def sent(template_id: TemplateId) -> StoredEvent:
    return TemplateSent(uuid4(), template_id)


def shown(intent: Intent, product: ProductKey | None = None, language: TurnLanguage = "es") -> StoredEvent:
    return ShownTurn(uuid4(), "es", intent, product, language, None, None, 0, False, "", None)


def analysis(outcome: Outcome, product: ProductKey = "credit_card") -> StoredEvent:
    return AnalysisCompleted(uuid4(), outcome, product, "es", "alba-credit-v1")


def test_a_first_turn_has_no_asks_and_no_income_request() -> None:
    assert stamp_turn([], None, None) == TurnStamp(product=None, product_asked_count=0, income_requested=False)


def test_the_product_the_model_read_wins_over_the_stored_one() -> None:
    assert stamp_turn([], "personal_loan", "credit_card").product == "personal_loan"


def test_a_turn_with_no_product_takes_the_stored_one() -> None:
    assert stamp_turn([], None, "credit_card").product == "credit_card"


def test_a_turn_naming_a_product_with_its_own_open_case_keeps_the_case_and_names_the_other() -> None:
    stamp = stamp_turn([], "personal_loan", "credit_card", frozenset({"personal_loan"}))
    assert (stamp.product, stamp.open_case_product) == ("credit_card", "personal_loan")


def test_a_turn_naming_the_case_product_is_no_clash_even_when_another_case_holds_it() -> None:
    stamp = stamp_turn([], "credit_card", "credit_card", frozenset({"credit_card"}))
    assert (stamp.product, stamp.open_case_product) == ("credit_card", None)


def test_a_turn_naming_a_product_with_no_open_case_switches_the_case_to_it() -> None:
    stamp = stamp_turn([], "personal_loan", "credit_card", frozenset())
    assert (stamp.product, stamp.open_case_product) == ("personal_loan", None)


def test_the_which_product_template_and_a_shown_clarification_each_count_as_an_ask() -> None:
    earlier = [shown("clarify"), sent("which_product"), shown("clarify", language="pt")]
    assert stamp_turn(earlier, None, None).product_asked_count == 3


@pytest.mark.parametrize(
    "event",
    [
        shown("clarify", product="credit_card"),
        shown("clarify", language="other"),
        shown("chit_chat"),
        WithheldTurn(uuid4(), "es", "reply_forbidden"),
        sent("confirm_prequalify"),
        sent("needs_income"),
    ],
    ids=["clarify-with-product", "clarify-in-other-language", "chit-chat", "withheld", "consent", "income"],
)
def test_an_event_that_did_not_ask_which_product_is_not_counted(event: StoredEvent) -> None:
    assert stamp_turn([event], None, None).product_asked_count == 0


def test_income_is_requested_after_needs_info_for_the_same_product() -> None:
    assert stamp_turn([analysis("NEEDS_INFO"), sent("needs_income")], None, "credit_card").income_requested is True


def test_income_is_not_requested_for_another_product() -> None:
    assert stamp_turn([analysis("NEEDS_INFO")], "personal_loan", "credit_card").income_requested is False


@pytest.mark.parametrize("outcome", ["PREQUALIFIED", "NOT_PREQUALIFIED", "REFER"])
def test_income_is_not_requested_after_another_outcome(outcome: Outcome) -> None:
    assert stamp_turn([analysis(outcome)], None, "credit_card").income_requested is False


@pytest.mark.parametrize(
    "later", [sent("confirm_prequalify"), shown("decline_prequalify")], ids=["consent-asked", "declined"]
)
def test_a_new_consent_question_or_a_decline_withdraws_the_income_request(later: StoredEvent) -> None:
    assert stamp_turn([analysis("NEEDS_INFO"), later], None, "credit_card").income_requested is False


def test_only_the_latest_analysis_decides_the_income_request() -> None:
    earlier = [analysis("REFER"), analysis("NEEDS_INFO"), sent("needs_income")]
    assert stamp_turn(earlier, None, "credit_card").income_requested is True
    assert stamp_turn([*earlier, analysis("PREQUALIFIED")], None, "credit_card").income_requested is False


def test_a_decline_before_the_analysis_does_not_withdraw_its_request() -> None:
    earlier = [shown("decline_prequalify"), analysis("NEEDS_INFO")]
    assert stamp_turn(earlier, None, "credit_card").income_requested is True
