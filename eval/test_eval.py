import dataclasses
from pathlib import Path
from uuid import uuid4

import pytest

from api.domain.process.turns import ShownReading, WithheldReading
from api.infrastructure.llm.conversation import LlmCall
from api.infrastructure.llm.keywords import read_keyword_turn
from eval.heldout import ChangedHeldOutSet, HeldOutItem, load_heldout
from eval.metrics import percentile, wilson
from eval.report import markdown
from eval.routes import FAILED_READ, expected_reading, route_of
from eval.run_eval import cost_usd, run, summary

ITEMS = {item.item_id: item for item in load_heldout()}


def test_the_frozen_set_has_sixty_items_in_seven_slices() -> None:
    assert len(ITEMS) == 60
    assert {item.slice for item in ITEMS.values()} == {"es-mx", "es-co", "es-ar", "pt", "mixed", "other", "adversarial"}


def test_a_changed_set_is_refused(tmp_path: Path) -> None:
    changed = tmp_path / "v1.jsonl"
    changed.write_text("{}\n")
    with pytest.raises(ChangedHeldOutSet, match="no longer matches its frozen sha256"):
        load_heldout(changed)


@pytest.mark.parametrize(
    ("item_id", "rules", "product"),
    [
        ("h06", ("run_policy",), "credit_card"),
        ("h08", ("hand_off_human",), None),
        ("h05", ("run_policy_income",), "credit_card"),
        ("h52", ("hand_off_language",), None),
        ("h02", ("ask_confirm_prequalify",), None),
    ],
    ids=["a yes runs the card", "a person", "an income", "english", "a switch asks consent"],
)
def test_the_gold_labels_route_through_the_engine(item_id: str, rules: tuple[str, ...], product: str | None) -> None:
    route = route_of(expected_reading(ITEMS[item_id]), ITEMS[item_id])
    assert (route.rules, route.policy_product) == (rules, product)


def test_a_withheld_reading_goes_to_a_person_and_a_failed_read_counts_as_a_handoff() -> None:
    item = ITEMS["h06"]
    withheld = WithheldReading(expected_reading(item).reading, "reply_forbidden")
    assert route_of(withheld, item).rules == ("hand_off_reply",)
    assert FAILED_READ.hands_off and not FAILED_READ.runs_policy


def test_the_interval_holds_zero_and_half() -> None:
    none = wilson(0, 60)
    half = wilson(30, 60)
    assert (none.low, round(none.high, 4)) == (0.0, 0.0602)
    assert (round(half.low, 3), round(half.high, 3)) == (0.377, 0.623)
    assert wilson(0, 0).total == 0


def test_the_percentile_is_the_nearest_rank() -> None:
    assert percentile([30.0, 10.0, 20.0, 40.0], 0.5) == 20.0
    assert percentile([30.0, 10.0, 20.0, 40.0], 0.95) == 40.0
    assert percentile([], 0.5) == 0.0


def test_a_call_costs_its_tokens_at_the_list_price() -> None:
    call = LlmCall(
        process_id=uuid4(),
        command_id=uuid4(),
        model="claude-sonnet-5-5",
        request={},
        raw_response="{}",
        parsed=None,
        parse_ok=False,
        input_tokens=2000,
        cached_input_tokens=1000,
        cache_write_input_tokens=500,
        output_tokens=100,
        latency_ms=900,
    )
    assert cost_usd(call) == pytest.approx((500 * 2.00 + 1000 * 0.20 + 500 * 2.50 + 100 * 10.00) / 1_000_000)


def test_b0_runs_offline_and_its_report_renders() -> None:
    scored = run(list(ITEMS.values()), read_keyword_turn, [])
    numbers = summary(scored)
    assert (numbers["n"], numbers["calls"], numbers["cost_usd"]) == (60, 0, 0)
    payload = {
        "date": "2026-10-05",
        "heldout_sha256": "x",
        "prompt_version": "alba-turn-v1",
        "effort": "low",
        "systems": {"b0-keywords": numbers},
        "slices": {"b0-keywords": {"pt": {"intent": numbers["intent"], "route": numbers["route"]}}},
        "misses": {"b0-keywords": []},
    }
    report = markdown(payload)
    assert "| Route (rules the engine fires) |" in report and "### b0-keywords: 0 items off" in report


def test_a_reader_that_fails_is_scored_as_a_failed_read() -> None:
    def broken(_request: object) -> ShownReading:
        raise RuntimeError("down")

    [one] = run([ITEMS["h06"]], broken, [])
    assert (one.reading, one.route, one.error) == (None, FAILED_READ, "RuntimeError: down")
    assert not one.route_ok and not one.intent_ok


def test_an_item_keeps_its_context() -> None:
    item: HeldOutItem = ITEMS["h05"]
    assert dataclasses.astuple(item.context) == ("credit_card", True, 0)
