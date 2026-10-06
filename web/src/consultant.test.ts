import { describe, expect, it } from "vitest";

import { closeActions, closeAnswerOf, packetRows } from "./consultant";
import { ALICIA, BEFORE_THE_POLICY, JULIANA } from "./consultant.fixtures";
import { es } from "./i18n/es";

const productName = (product: keyof typeof es.products.askAbout) => es.products.askAbout[product];

describe("the handoff packet", () => {
  it("shows Alicia's request, score, income, rule, policy, outcome, and reason", () => {
    expect(packetRows(ALICIA, productName)).toEqual([
      { field: "request", value: "Tarjeta de crédito", identifier: false },
      { field: "score", value: "615", identifier: false },
      { field: "income", value: "4,707,334.28 COP", identifier: false },
      { field: "rule", value: "R05", identifier: true },
      { field: "policy", value: "alba-credit-v1", identifier: true },
      { field: "outcome", value: "REFER", identifier: true },
      { field: "reason", value: "policy_refer", identifier: true },
    ]);
  });

  it("shows Juliana's NEEDS_INFO by R06 and why she reached a person, with no income row", () => {
    expect(packetRows(JULIANA, productName)).toEqual([
      { field: "request", value: "Tarjeta de crédito", identifier: false },
      { field: "score", value: "714", identifier: false },
      { field: "rule", value: "R06", identifier: true },
      { field: "policy", value: "alba-credit-v1", identifier: true },
      { field: "outcome", value: "NEEDS_INFO", identifier: true },
      { field: "reason", value: "customer_requested_human", identifier: true },
    ]);
  });

  it("shows only the reason for a case handed off before the policy ran", () => {
    expect(packetRows(BEFORE_THE_POLICY, productName)).toEqual([
      { field: "reason", value: "tool_failed", identifier: true },
    ]);
  });
});

describe("the close", () => {
  it("offers both outcomes, pre-qualify first, only when the packet says closable", () => {
    expect(closeActions(ALICIA, null)).toEqual(["PREQUALIFIED", "NOT_PREQUALIFIED"]);
    expect(closeActions(JULIANA, null)).toEqual([]);
    expect(closeActions(BEFORE_THE_POLICY, null)).toEqual([]);
  });

  it("does not offer a close again once one is written or still settling, and does after a failed send", () => {
    expect(closeActions(ALICIA, { kind: "pending" })).toEqual([]);
    expect(closeActions(ALICIA, { kind: "already_closed" })).toEqual([]);
    expect(closeActions(ALICIA, { kind: "failed" })).toEqual(["PREQUALIFIED", "NOT_PREQUALIFIED"]);
  });

  it.each([
    [200, undefined, "closed"],
    [409, "already_closed", "already_closed"],
    [409, "case_not_closable", "not_closable"],
    [404, "not_found", "gone"],
    [503, "cycle_pending", "pending"],
    [409, "case_ended", "failed"],
    [422, "invalid_body", "failed"],
    [500, undefined, "failed"],
    [null, undefined, "failed"],
  ] as const)("reads a %s %s as %s", (status, error, kind) => {
    expect(closeAnswerOf(status, error)).toEqual({ kind });
  });
});
