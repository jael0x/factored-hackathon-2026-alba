import type { components } from "./api/schema";
import { CONFLICT, CYCLE_PENDING, NOT_FOUND, OK } from "./api/status";
import { NOT_PREQUALIFIED, PREQUALIFIED } from "./chat";
import { formatAmount } from "./format";

type ConsultantCase = components["schemas"]["ConsultantCase"];
type CloseOutcome = components["schemas"]["CloseOutcome"];
type ProductKey = components["schemas"]["ProductKey"];
type AlreadyClosed = components["schemas"]["AlreadyClosedError"]["error"];
type CaseConflict = components["schemas"]["CaseConflictError"]["error"];

export type PacketField = "request" | "score" | "income" | "rule" | "policy" | "outcome" | "reason";

export type PacketRow = { field: PacketField; value: string; identifier: boolean };

// What the consultant sees of a case: the packet while a person has it, or that it no longer waits for one (404).
export type ConsultantCaseLoad = { kind: "open"; packet: ConsultantCase } | { kind: "gone" };

export type CloseAnswer =
  | { kind: "closed" }
  | { kind: "already_closed" }
  | { kind: "not_closable" }
  | { kind: "gone" }
  | { kind: "pending" }
  | { kind: "failed" };

// DESIGN.md "Consultant case": "Precalificar", then "No precalificar", the same weight.
const CLOSE_OUTCOMES: readonly CloseOutcome[] = [PREQUALIFIED, NOT_PREQUALIFIED];

const ALREADY_CLOSED: AlreadyClosed = "already_closed";
const CASE_NOT_CLOSABLE: CaseConflict = "case_not_closable";

// The API decides whether a case can be closed (PLAN.md D15 (3)); the screen only offers what closable allows.
// A close already written, or still settling, is not offered again until the case is read once more.
export function closeActions(packet: ConsultantCase, answer: CloseAnswer | null): readonly CloseOutcome[] {
  const written = answer?.kind === "already_closed" || answer?.kind === "pending";
  return packet.closable && !written ? CLOSE_OUTCOMES : [];
}

// A field the packet carries as null has no row: a case the policy never read shows only why it reached a person.
export function packetRows(packet: ConsultantCase, productName: (product: ProductKey) => string): PacketRow[] {
  const income =
    packet.income_local === null || packet.income_currency === null
      ? null
      : `${formatAmount(packet.income_local)} ${packet.income_currency}`;
  const rows: [PacketField, string | null, boolean][] = [
    ["request", packet.product === null ? null : productName(packet.product), false],
    ["score", packet.credit_score === null ? null : String(packet.credit_score), false],
    ["income", income, false],
    ["rule", packet.deciding_rule, true],
    ["policy", packet.policy_version, true],
    ["outcome", packet.outcome, true],
    ["reason", packet.reason_code, true],
  ];
  return rows.flatMap(([field, value, identifier]) => (value === null ? [] : [{ field, value, identifier }]));
}

// A 503 means the close was written and its cycle still runs: the screen reads the case again, never closes twice.
export function closeAnswerOf(status: number | null, error: string | undefined): CloseAnswer {
  if (status === OK) {
    return { kind: "closed" };
  }
  if (status === CONFLICT && error === ALREADY_CLOSED) {
    return { kind: "already_closed" };
  }
  if (status === CONFLICT && error === CASE_NOT_CLOSABLE) {
    return { kind: "not_closable" };
  }
  if (status === NOT_FOUND) {
    return { kind: "gone" };
  }
  if (status === CYCLE_PENDING) {
    return { kind: "pending" };
  }
  return { kind: "failed" };
}

export function isGone(status: number): boolean {
  return status === NOT_FOUND;
}
