import type { components } from "./api/schema";
import { OUTCOME_TONE, STATE_TONE, type Tone } from "./tones";

type TraceEvent = components["schemas"]["TraceEvent"];
type TurnClassified = components["schemas"]["TraceTurnClassified"];
type AnalysisCompleted = components["schemas"]["TraceAnalysisCompleted"];
type Fact = components["schemas"]["Fact"];
type RuleTraceStep = components["schemas"]["RuleTraceStep"];
type RuleTraceResult = components["schemas"]["RuleTraceResult"];
type Outcome = components["schemas"]["Outcome"];
type ProcessState = components["schemas"]["ProcessState"];

export type TraceWord = "by" | "to" | "policy";

export type DetailPart =
  | { kind: "quote"; text: string }
  | { kind: "identifier"; text: string }
  | { kind: "tag"; text: string; tone: Tone }
  | { kind: "word"; word: TraceWord }
  | { kind: "separator" };

export type RuleRow = { rule: string; result: DetailPart; inputs: { name: string; value: string }[] };

export type FactRow = { name: string; value: string; source: string; asOf: string };

export type TraceLink = { from: number; to: number; lane: number };

export type UnresolvedCause = { eventId: string; causeId: string };

export type TraceLinks = { links: TraceLink[]; unresolved: UnresolvedCause[] };

const BY: DetailPart = { kind: "word", word: "by" };
const TO: DetailPart = { kind: "word", word: "to" };
const POLICY: DetailPart = { kind: "word", word: "policy" };
const SEPARATOR: DetailPart = { kind: "separator" };

const identifier = (text: string): DetailPart => ({ kind: "identifier", text });
const outcomeTag = (outcome: Outcome): DetailPart => ({ kind: "tag", text: outcome, tone: OUTCOME_TONE[outcome] });
const stateTag = (state: ProcessState): DetailPart => ({ kind: "tag", text: state, tone: STATE_TONE[state] });

function joined(groups: DetailPart[][]): DetailPart[] {
  return groups.filter((group) => group.length > 0).flatMap((group, index) => (index === 0 ? group : [SEPARATOR, ...group]));
}

// The trace is the record: a value is shown as the API wrote it, never rounded or grouped.
export function recordedValue(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }
  if (value === null || typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

function declaredIncome(amount: number, currency: TurnClassified["declared_income_currency"]): DetailPart {
  const value = recordedValue(amount);
  return identifier(currency === null ? value : `${value} ${currency}`);
}

function turnDetail(turn: TurnClassified): DetailPart[] {
  const amount = turn.declared_income_amount;
  const income = amount === null ? [] : [declaredIncome(amount, turn.declared_income_currency)];
  const withheld = turn.reply_ok || turn.reason_code === null ? [] : [identifier(turn.reason_code)];
  return joined([
    [identifier(turn.intent)],
    turn.product === null ? [] : [identifier(turn.product)],
    [identifier(turn.language)],
    income,
    withheld,
  ]);
}

// specs/09-case-trace.feature gives each event name its detail; a new event name fails tsc here until it has one.
export function traceDetail(event: TraceEvent): DetailPart[] {
  switch (event.event_name) {
    case "conversation.message_received":
      return [{ kind: "quote", text: event.text }];
    case "process.started":
      return [identifier(event.process_key)];
    case "conversation.turn_classified":
      return turnDetail(event);
    case "conversation.template_sent":
      return [identifier(event.template_id)];
    case "conversation.consultant_closed":
      return [outcomeTag(event.outcome), BY, identifier(event.consultant_id)];
    case "conversation.thread_taken":
      return [identifier(event.reason_code)];
    case "analysis.completed":
      return [outcomeTag(event.outcome), BY, identifier(event.deciding_rule)];
    case "prequalification.decided":
      return joined([[outcomeTag(event.outcome)], [identifier(event.decided_by)]]);
    case "process.state_changed":
      return joined([
        [stateTag(event.from_state), TO, stateTag(event.to_state)],
        event.end_reason === null ? [] : [identifier(event.end_reason)],
      ]);
    case "process.ended":
      return joined([
        [identifier(event.end_reason)],
        event.policy_version === null ? [] : [POLICY, identifier(event.policy_version)],
      ]);
    case "conversation.appeal_requested":
      return [identifier(event.product)];
  }
}

export function analysisOf(event: TraceEvent): AnalysisCompleted | null {
  return event.event_name === "analysis.completed" ? event : null;
}

function isOutcome(result: RuleTraceResult): result is Outcome {
  return Object.hasOwn(OUTCOME_TONE, result);
}

export function ruleRows(steps: readonly RuleTraceStep[]): RuleRow[] {
  return steps.map((step) => ({
    rule: step.rule_id,
    result: isOutcome(step.result) ? outcomeTag(step.result) : identifier(step.result),
    inputs: Object.entries(step.input).map(([name, value]) => ({ name, value: recordedValue(value) })),
  }));
}

export function factRows(facts: readonly Fact[]): FactRow[] {
  return facts.map((fact) => ({
    name: fact.name,
    value: recordedValue(fact.value),
    source: fact.source,
    asOf: fact.as_of,
  }));
}

type Span = { from: number; to: number; top: number; bottom: number };

const bySpan = (a: Span, b: Span) => a.top - b.top || a.bottom - b.bottom || a.from - b.from;

// Interval coloring: a link takes the lowest lane whose last link ends above its top card, so links never overlap.
function inLanes(spans: Span[]): TraceLink[] {
  const laneBottoms: number[] = [];
  return [...spans].sort(bySpan).map(({ from, to, top, bottom }) => {
    const free = laneBottoms.findIndex((laneBottom) => laneBottom < top);
    const lane = free === -1 ? laneBottoms.length : free;
    laneBottoms[lane] = bottom;
    return { from, to, lane };
  });
}

// A link is the id the event wrote in caused_by_event_id, found by id in this list: never by time or by position.
export function traceLinks(events: readonly TraceEvent[]): TraceLinks {
  const position = new Map(events.map((event, index) => [event.id, index]));
  const causes = events.flatMap((event, from) =>
    event.caused_by_event_id === null ? [] : [{ from, eventId: event.id, causeId: event.caused_by_event_id }],
  );
  const spans = causes.flatMap(({ from, causeId }) => {
    const to = position.get(causeId);
    return to === undefined ? [] : [{ from, to, top: Math.min(from, to), bottom: Math.max(from, to) }];
  });
  const unresolved = causes
    .filter(({ causeId }) => !position.has(causeId))
    .map(({ eventId, causeId }) => ({ eventId, causeId }));
  return { links: inLanes(spans), unresolved };
}

export function causeOf(links: readonly TraceLink[]): ReadonlyMap<number, number> {
  return new Map(links.map((link) => [link.from, link.to]));
}
