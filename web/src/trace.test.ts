import { describe, expect, it } from "vitest";

import type { components } from "./api/schema";
import { causeOf, factRows, recordedValue, ruleRows, traceDetail, traceLinks, type DetailPart, type TraceWord } from "./trace";
import { ALICIA_ANALYSIS, ALICIA_MESSAGE, ALICIA_STARTED, ALICIA_TRACE, EVERY_EVENT } from "./trace.fixtures";

type TraceEvent = components["schemas"]["TraceEvent"];
type EventName = components["schemas"]["EventName"];

// specs/09 writes the detail in English; the screen takes the same words from i18n.
const SPEC_WORDS: Record<TraceWord, string> = { by: "by", to: "to", policy: "policy" };

function partText(part: DetailPart): string {
  if (part.kind === "word") {
    return SPEC_WORDS[part.word];
  }
  return part.kind === "separator" ? "·" : part.text;
}

const detailText = (event: TraceEvent) => traceDetail(event).map(partText).join(" ");

const MESSAGE = ALICIA_MESSAGE;
const STARTED = ALICIA_STARTED;

describe("the trace of Alicia's referred case (specs/09)", () => {
  it("lists the events in the order the API wrote them, each with its detail", () => {
    expect(ALICIA_TRACE.events.map((event) => [event.event_name, detailText(event)])).toEqual([
      ["conversation.message_received", "Quiero una tarjeta de crédito"],
      ["process.started", "credit_prequalification"],
      ["analysis.completed", "REFER by R05"],
      ["process.state_changed", "ai_active to human_active"],
      ["conversation.thread_taken", "policy_refer"],
      ["conversation.template_sent", "refer_notice"],
    ]);
  });

  it("tags the outcome and the states in their tones", () => {
    const tags = (event: TraceEvent) => traceDetail(event).filter((part) => part.kind === "tag");
    expect(tags(ALICIA_ANALYSIS)).toEqual([{ kind: "tag", text: "REFER", tone: "clay" }]);
    expect(tags(ALICIA_TRACE.events[3])).toEqual([
      { kind: "tag", text: "ai_active", tone: "slate" },
      { kind: "tag", text: "human_active", tone: "clay" },
    ]);
  });

  it("cites the facts behind the decision as recorded", () => {
    expect(factRows(ALICIA_ANALYSIS.facts)).toEqual([
      { name: "credit_score", value: "615", source: "customer_credit_profile.credit_score", asOf: "2026-06-17" },
      { name: "income_local", value: "4707334.28", source: "customer_credit_profile.income_local", asOf: "2026-06-17" },
      { name: "income_currency", value: "COP", source: "customer_credit_profile.income_currency", asOf: "2026-06-17" },
      { name: "income_usd", value: "1167.41890144", source: "customer_credit_profile.income_usd", asOf: "2026-06-17" },
    ]);
  });

  it("lists the rules the analysis evaluated, in order, with each result and its input", () => {
    const rows = ruleRows(ALICIA_ANALYSIS.rule_trace);
    expect(rows.map((row) => [row.rule, partText(row.result)])).toEqual([
      ["R01", "passed"],
      ["R02", "passed"],
      ["R03", "passed"],
      ["R09", "passed"],
      ["R04", "passed"],
      ["R06", "passed"],
      ["R05", "REFER"],
    ]);
    expect(rows[6].result).toEqual({ kind: "tag", text: "REFER", tone: "clay" });
    expect(rows[5].inputs).toEqual([
      { name: "income_local", value: "4707334.28" },
      { name: "declared_income", value: "null" },
      { name: "income_currency", value: "COP" },
    ]);
  });
});

describe("the detail of every event name (specs/09)", () => {
  const EXPECTED: Record<EventName, string> = {
    "conversation.message_received": "gano 45000 pesos",
    "process.started": "credit_prequalification",
    "conversation.turn_classified": "provide_income · personal_loan · es · 45000 MXN",
    "conversation.template_sent": "needs_income",
    "conversation.consultant_closed": "PREQUALIFIED by AGT-00042",
    "conversation.thread_taken": "customer_requested_human",
    "analysis.completed": "NEEDS_INFO by R06",
    "prequalification.decided": "NOT_PREQUALIFIED · policy",
    "process.state_changed": "ai_active to ended · not_prequalified",
    "process.ended": "not_prequalified · policy alba-credit-v1",
    "conversation.appeal_requested": "personal_loan",
  };

  it.each(Object.values(EVERY_EVENT))("$event_name", (event) => {
    expect(detailText(event)).toBe(EXPECTED[event.event_name]);
  });

  const turn = EVERY_EVENT["conversation.turn_classified"];

  it("names the reason of a withheld reply", () => {
    expect(detailText({ ...turn, reply_ok: false, reason_code: "reply_forbidden" })).toBe(
      "provide_income · personal_loan · es · 45000 MXN · reply_forbidden",
    );
  });

  it("leaves out what the turn did not read", () => {
    const bare = { ...turn, product: null, declared_income_amount: null, declared_income_currency: null };
    expect(detailText({ ...bare, intent: "clarify" })).toBe("clarify · es");
    expect(detailText({ ...bare, declared_income_amount: 45000 })).toBe("provide_income · es · 45000");
  });

  it("names no policy on an end a consultant decided", () => {
    expect(detailText({ ...EVERY_EVENT["process.ended"], policy_version: null })).toBe("not_prequalified");
  });
});

describe("a recorded value", () => {
  it.each([
    [1167.41890144, "1167.41890144"],
    [4707334.28, "4707334.28"],
    [615, "615"],
    [null, "null"],
    [false, "false"],
    ["COP", "COP"],
    [{ band: [580, 619] }, '{"band":[580,619]}'],
  ])("%j reads %s", (value, text) => {
    expect(recordedValue(value)).toBe(text);
  });
});

describe("the links between events", () => {
  it("joins each event to the one its caused_by_event_id names, in lanes that never overlap", () => {
    const { links, unresolved } = traceLinks(ALICIA_TRACE.events);
    expect(links).toEqual([
      { from: 1, to: 0, lane: 0 },
      { from: 2, to: 1, lane: 1 },
      { from: 3, to: 2, lane: 0 },
      { from: 4, to: 2, lane: 2 },
      { from: 5, to: 4, lane: 0 },
    ]);
    expect(unresolved).toEqual([]);
    expect([...causeOf(links)].sort(([a], [b]) => a - b)).toEqual([
      [1, 0],
      [2, 1],
      [3, 2],
      [4, 2],
      [5, 4],
    ]);
  });

  it("finds the cause by id, whatever the position", () => {
    const reversed = [...ALICIA_TRACE.events].reverse();
    const joined = traceLinks(reversed).links.map((link) => [reversed[link.from].id, reversed[link.to].id]);
    const expected = traceLinks(ALICIA_TRACE.events).links.map((link) => [
      ALICIA_TRACE.events[link.from].id,
      ALICIA_TRACE.events[link.to].id,
    ]);
    expect(joined.sort()).toEqual(expected.sort());
  });

  it("draws no link for an event with no cause", () => {
    expect(traceLinks([MESSAGE]).links).toEqual([]);
  });

  it("draws no link to a cause the list does not hold, and reports it", () => {
    expect(traceLinks([STARTED])).toEqual({
      links: [],
      unresolved: [{ eventId: STARTED.id, causeId: MESSAGE.id }],
    });
  });

  it("gives two links that share a card different lanes, and two apart the same lane", () => {
    const lanes = traceLinks(ALICIA_TRACE.events).links;
    const spans = lanes.map((link) => ({ lane: link.lane, top: Math.min(link.from, link.to), bottom: Math.max(link.from, link.to) }));
    const overlapping = spans.flatMap((a, i) =>
      spans.slice(i + 1).filter((b) => a.lane === b.lane && a.top <= b.bottom && b.top <= a.bottom),
    );
    expect(overlapping).toEqual([]);
  });
});
