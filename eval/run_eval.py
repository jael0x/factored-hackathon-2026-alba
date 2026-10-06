"""B0 against Claude on the frozen held-out set (IMPLEMENTATION.md M4, M6), with M2's latency and cost.

Needs ANTHROPIC_API_KEY for Claude; B0 runs offline. Run from the repo root in the api container:

    docker compose run --rm --no-deps -v "$PWD:/work" -w /work api python -m eval.run_eval
"""

import argparse
import json
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from api.application.cycle.ports import ReadTurn, TurnRequest
from api.domain.process.lifecycle import AI_ACTIVE
from api.domain.process.stored_events import CONFIRM_PREQUALIFY_INTENT, PROVIDE_INCOME_INTENT
from api.domain.process.turns import ModelReading, WithheldReading
from api.infrastructure.config.settings import claude_access, settings
from api.infrastructure.llm.conversation import CLAUDE_SONNET_5_5, EFFORT, LlmCall, claude_turn_reader
from api.infrastructure.llm.keywords import B0_MODEL, read_keyword_turn
from api.infrastructure.llm.prompt import PROMPT_VERSION
from eval.heldout import HELDOUT_SHA256, HeldOutItem, load_heldout
from eval.metrics import Rate, percentile, wilson
from eval.report import markdown
from eval.routes import FAILED_READ, Route, expected_reading, route_of

REPORTS = Path(__file__).resolve().parent / "reports"
PROCESS_ID = UUID("11111111-1111-4111-8111-111111111111")
COMMAND_ID = UUID("33333333-3333-4333-8333-333333333333")
# USD per 1M tokens, Claude API list prices for Claude Sonnet 5.5 (claude-api reference, cached 2026-09-25).
# The turns that may state an amount: an income alone, or a yes that also states one.
INCOME_INTENTS = frozenset({PROVIDE_INCOME_INTENT, CONFIRM_PREQUALIFY_INTENT})
PRICES = {"input": 2.00, "cache_read": 0.20, "cache_write": 2.50, "output": 10.00}


@dataclass(frozen=True)
class Scored:
    item: HeldOutItem
    reading: ModelReading | None
    route: Route
    expected: Route
    latency_ms: float
    calls: tuple[LlmCall, ...]
    error: str | None

    @property
    def intent_ok(self) -> bool:
        return self.reading is not None and self.reading.reading.intent == self.item.expected.intent

    @property
    def product_ok(self) -> bool:
        return self.reading is not None and self.reading.reading.product == self.item.expected.product

    @property
    def language_ok(self) -> bool:
        return self.reading is not None and self.reading.reading.language == self.item.expected.language

    @property
    def amount_ok(self) -> bool:
        gold, read = self.item.expected, self.reading
        return read is not None and (read.reading.declared_income_amount, read.reading.declared_income_currency) == (
            gold.declared_income_amount,
            gold.declared_income_currency,
        )

    @property
    def route_ok(self) -> bool:
        return not self.route.failed and self.route.rules == self.expected.rules


def request_of(item: HeldOutItem) -> TurnRequest:
    on_file = not item.context.income_requested
    return TurnRequest(PROCESS_ID, COMMAND_ID, item.text, item.locale, AI_ACTIVE, on_file, True, False, False)


def score(item: HeldOutItem, read: ReadTurn, calls: list[LlmCall]) -> Scored:
    before = len(calls)
    started = time.monotonic()
    try:
        reading: ModelReading | None = read(request_of(item))
        error = None
    # A failed read is an outcome of the run, not an end to it: the product's worker hands that case to a person.
    except Exception as failure:  # noqa: BLE001
        reading, error = None, f"{type(failure).__name__}: {failure}"
    latency_ms = (time.monotonic() - started) * 1000
    route = FAILED_READ if reading is None else route_of(reading, item)
    return Scored(
        item, reading, route, route_of(expected_reading(item), item), latency_ms, tuple(calls[before:]), error
    )


def run(items: Sequence[HeldOutItem], read: ReadTurn, calls: list[LlmCall]) -> list[Scored]:
    return [score(item, read, calls) for item in items]


def rate(scored: Sequence[Scored], hit: Callable[[Scored], bool]) -> Rate:
    return wilson(sum(1 for one in scored if hit(one)), len(scored))


def cost_usd(call: LlmCall) -> float:
    uncached = call.input_tokens - call.cached_input_tokens - call.cache_write_input_tokens
    return (
        uncached * PRICES["input"]
        + call.cached_input_tokens * PRICES["cache_read"]
        + call.cache_write_input_tokens * PRICES["cache_write"]
        + call.output_tokens * PRICES["output"]
    ) / 1_000_000


def summary(scored: Sequence[Scored]) -> dict[str, object]:
    amounts = [one for one in scored if one.item.expected.intent in INCOME_INTENTS]
    calls = [call for one in scored for call in one.calls]
    return {
        "n": len(scored),
        "valid_output": rate(scored, lambda one: one.reading is not None),
        "intent": rate(scored, lambda one: one.intent_ok),
        "product": rate(scored, lambda one: one.product_ok),
        "language": rate(scored, lambda one: one.language_ok),
        "amount_and_currency": rate(amounts, lambda one: one.amount_ok),
        "route": rate(scored, lambda one: one.route_ok),
        "unsafe_policy_without_consent": rate(scored, lambda o: o.route.runs_policy and not o.expected.runs_policy),
        "unsafe_wrong_product_run": rate(
            scored,
            lambda o: o.route.runs_policy
            and o.expected.runs_policy
            and o.route.policy_product != o.expected.policy_product,
        ),
        "unsafe_missed_handoff": rate(scored, lambda o: o.expected.hands_off and not o.route.hands_off),
        "unneeded_handoff": rate(scored, lambda o: o.route.hands_off and not o.expected.hands_off),
        "reply_withheld": rate(scored, lambda o: isinstance(o.reading, WithheldReading)),
        "latency_ms_p50": percentile([one.latency_ms for one in scored], 0.5),
        "latency_ms_p95": percentile([one.latency_ms for one in scored], 0.95),
        "calls": len(calls),
        "input_tokens": sum(call.input_tokens for call in calls),
        "cached_input_tokens": sum(call.cached_input_tokens for call in calls),
        "output_tokens": sum(call.output_tokens for call in calls),
        "cost_usd": sum(cost_usd(call) for call in calls),
    }


def by_slice(scored: Sequence[Scored]) -> dict[str, dict[str, Rate]]:
    slices = sorted({one.item.slice for one in scored})
    return {
        name: {
            "intent": rate([o for o in scored if o.item.slice == name], lambda o: o.intent_ok),
            "route": rate([o for o in scored if o.item.slice == name], lambda o: o.route_ok),
        }
        for name in slices
    }


def misses(scored: Sequence[Scored]) -> list[dict[str, object]]:
    return [
        {
            "id": one.item.item_id,
            "slice": one.item.slice,
            "text": one.item.text,
            "expected_intent": one.item.expected.intent,
            "read_intent": None if one.reading is None else one.reading.reading.intent,
            "expected_product": one.item.expected.product,
            "read_product": None if one.reading is None else one.reading.reading.product,
            "expected_route": list(one.expected.rules),
            "route": ["failed read"] if one.route.failed else list(one.route.rules),
            "error": one.error,
        }
        for one in scored
        if not (one.route_ok and one.intent_ok and one.product_ok and one.language_ok and one.amount_ok)
    ]


def claude_reader(model: str, calls: list[LlmCall]) -> ReadTurn:
    if not settings.anthropic_api_key:
        raise SystemExit("ANTHROPIC_API_KEY is not set: put it in .env and run in the api container")
    return claude_turn_reader(claude_access(), model, calls.append)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=CLAUDE_SONNET_5_5)
    parser.add_argument("--b0-only", action="store_true")
    args = parser.parse_args(argv)
    items = load_heldout()
    results: dict[str, list[Scored]] = {B0_MODEL: run(items, read_keyword_turn, [])}
    if not args.b0_only:
        calls: list[LlmCall] = []
        results[args.model] = run(items, claude_reader(args.model, calls), calls)
    write_report(results)


def write_report(results: dict[str, list[Scored]]) -> None:
    stamp = datetime.now(UTC)
    payload = {
        "date": stamp.isoformat(timespec="seconds"),
        "heldout_sha256": HELDOUT_SHA256,
        "prompt_version": PROMPT_VERSION,
        "effort": EFFORT,
        "prices_usd_per_mtok": PRICES,
        "systems": {name: summary(scored) for name, scored in results.items()},
        "slices": {name: by_slice(scored) for name, scored in results.items()},
        "misses": {name: misses(scored) for name, scored in results.items()},
    }
    REPORTS.mkdir(exist_ok=True)
    name = f"{stamp:%Y-%m-%d-%H%M}-" + "-vs-".join(results)
    (REPORTS / f"{name}.json").write_text(json.dumps(payload, default=jsonable, ensure_ascii=False, indent=2) + "\n")
    (REPORTS / f"{name}.md").write_text(markdown(payload))
    print(markdown(payload))


def jsonable(value: object) -> object:
    if isinstance(value, Rate):
        return {"hits": value.hits, "total": value.total, "low": round(value.low, 4), "high": round(value.high, 4)}
    return str(value)


if __name__ == "__main__":
    main()
