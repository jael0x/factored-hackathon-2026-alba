from collections.abc import Mapping

from eval.metrics import Rate

QUALITY = (
    ("valid_output", "Valid output"),
    ("intent", "Intent"),
    ("product", "Product"),
    ("language", "Language read"),
    ("amount_and_currency", "Amount and currency (income turns)"),
    ("route", "Route (rules the engine fires)"),
)
SAFETY = (
    ("unsafe_policy_without_consent", "Policy run without consent"),
    ("unsafe_wrong_product_run", "Policy run on the wrong product"),
    ("unsafe_missed_handoff", "Missed handoff to a person"),
    ("unneeded_handoff", "Unneeded handoff (not unsafe)"),
    ("reply_withheld", "Reply withheld for stating an outcome"),
)


def cell(value: object) -> str:
    if not isinstance(value, Rate):
        return str(value)
    if value.total == 0:
        return "n/a"
    return f"{value.hits}/{value.total} ({value.share:.0%}, 95% CI {value.low:.0%} to {value.high:.0%})"


def table(rows: tuple[tuple[str, str], ...], systems: Mapping[str, Mapping[str, object]]) -> list[str]:
    names = list(systems)
    lines = ["| Metric | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    lines += [f"| {label} | " + " | ".join(cell(systems[name][key]) for name in names) + " |" for key, label in rows]
    return lines


def efficiency(systems: Mapping[str, Mapping[str, object]]) -> list[str]:
    lines = ["| System | Calls | p50 latency | p95 latency | Input tokens (cached) | Output tokens | Cost USD |"]
    lines.append("|---|---|---|---|---|---|---|")
    for name, numbers in systems.items():
        lines.append(
            f"| {name} | {numbers['calls']} | {float(str(numbers['latency_ms_p50'])):.0f} ms | "
            f"{float(str(numbers['latency_ms_p95'])):.0f} ms | {numbers['input_tokens']} ({numbers['cached_input_tokens']}) | "
            f"{numbers['output_tokens']} | {float(str(numbers['cost_usd'])):.4f} |"
        )
    return lines


def slices(by_system: Mapping[str, Mapping[str, Mapping[str, Rate]]]) -> list[str]:
    names = list(by_system)
    lines = ["| Slice | " + " | ".join(f"{name} intent | {name} route" for name in names) + " |"]
    lines.append("|---|" + "---|---|" * len(names))
    for slice_name in sorted(next(iter(by_system.values()))):
        cells = [cell(by_system[name][slice_name][metric]) for name in names for metric in ("intent", "route")]
        lines.append(f"| {slice_name} | " + " | ".join(cells) + " |")
    return lines


def miss_lines(misses: Mapping[str, list[Mapping[str, object]]]) -> list[str]:
    lines: list[str] = []
    for name, rows in misses.items():
        lines += [f"### {name}: {len(rows)} items off", ""]
        lines += [
            f'- `{row["id"]}` ({row["slice"]}) "{row["text"]}": intent {row["read_intent"]} for '
            f"{row['expected_intent']}; product {row['read_product']} for {row['expected_product']}; "
            f"route {joined(row['route'])} for {joined(row['expected_route'])}"
            + (f"; {row['error']}" if row["error"] else "")
            for row in rows
        ]
        lines.append("")
    return lines


def joined(value: object) -> str:
    return (", ".join(str(item) for item in value) or "none") if isinstance(value, list) else str(value)


def markdown(payload: Mapping[str, object]) -> str:
    systems = payload["systems"]
    by_slice = payload["slices"]
    misses = payload["misses"]
    if not isinstance(systems, Mapping) or not isinstance(by_slice, Mapping) or not isinstance(misses, Mapping):
        raise TypeError("the report payload needs systems, slices, and misses")
    lines = [
        "# Held-out evaluation: B0 against Claude",
        "",
        f"- Date: {payload['date']}",
        f"- Held-out set: `eval/heldout/v1.jsonl`, sha256 `{payload['heldout_sha256']}` (60 items; labels drafted "
        "with Claude Code by one team member, not yet reviewed by a second)",
        f"- Prompt: `{payload['prompt_version']}`, effort `{payload['effort']}`; one read and one retry per turn",
        "- Route: the process rules the engine fires on the turn the reading would write, against the rules the "
        "gold labels fire (`eval/routes.py`). A failed read counts as a handoff (the worker's `tool_failed`).",
        "- Intervals: Wilson 95%. Offline: no API, no database, one run per system.",
        "",
        "## Classification and route",
        "",
        *table(QUALITY, systems),
        "",
        "## Safety (counts over all 60 items)",
        "",
        *table(SAFETY, systems),
        "",
        "## Latency and cost (M2)",
        "",
        *efficiency(systems),
        "",
        "## By slice",
        "",
        *slices(by_slice),
        "",
        "## Items off",
        "",
        *miss_lines(misses),
    ]
    return "\n".join(lines) + "\n"
