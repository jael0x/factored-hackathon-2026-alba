import { MemoryRouter } from "react-router";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import type { components } from "../api/schema";
import type { Loaded } from "../api/useLoad";
import { es } from "../i18n/es";
import { renderForTest } from "../renderForTest";
import { ALICIA_MESSAGE, ALICIA_STARTED, ALICIA_TRACE } from "../trace.fixtures";
import { TraceState } from "./Trace";
import type { TraceLoad } from "./useTrace";

type CaseTrace = components["schemas"]["CaseTrace"];
type TraceEvent = components["schemas"]["TraceEvent"];

// jsdom lays nothing out and has no ResizeObserver; the connectors' geometry is checked in the browser.
beforeAll(() => {
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      disconnect() {}
    },
  );
});

afterEach(() => {
  vi.restoreAllMocks();
});

function render(trace: Loaded<TraceLoad>): HTMLElement {
  return renderForTest(
    <MemoryRouter>
      <TraceState trace={trace} onRetry={() => undefined} />
    </MemoryRouter>,
  );
}

const found = (trace: CaseTrace) => render({ status: "ready", data: { kind: "found", trace } });

const cards = (page: HTMLElement) => [...page.querySelectorAll(".trace-event")];
// The screen sets inline parts apart with a gap, not a space; this reads them the way the page shows them.
function text(node: Node | null | undefined): string | undefined {
  if (node === null || node === undefined) {
    return undefined;
  }
  if (node.nodeType === Node.TEXT_NODE) {
    return node.textContent?.trim();
  }
  return [...node.childNodes]
    .map(text)
    .filter((part) => part !== undefined && part !== "")
    .join(" ");
}

const MESSAGE = ALICIA_MESSAGE;
const STARTED = ALICIA_STARTED;

const STILL_WAITING: TraceEvent = {
  ...ALICIA_MESSAGE,
  id: "e0000007-0000-4000-8000-000000000007",
  created_at: "2026-10-05T14:10:00.000Z",
  process_id: ALICIA_TRACE.process_id,
  process_state: "human_active",
  text: "¿ya revisaron mi caso?",
  client_message_id: "c0000007-0000-4000-8000-000000000007",
  product: null,
};

describe("the trace screen (specs/09)", () => {
  it("numbers the events in the order the API returned them, each with its name and detail", () => {
    const page = found(ALICIA_TRACE);
    expect(
      cards(page).map((card) => [
        text(card.querySelector(".trace-marker")),
        text(card.querySelector(".trace-name")),
        text(card.querySelector(".trace-detail")),
      ]),
    ).toEqual([
      ["1", "conversation.message_received", "Quiero una tarjeta de crédito"],
      ["2", "process.started", "credit_prequalification"],
      ["3", "analysis.completed", "REFER por R05"],
      ["4", "conversation.template_sent", "refer_notice"],
      ["5", "process.state_changed", "ai_active a human_active"],
      ["6", "conversation.thread_taken", "policy_refer"],
    ]);
    expect(text(page.querySelector(".main-head"))).toBe(
      `${es.trace.title} ${es.trace.count(6)} ${ALICIA_TRACE.process_id}`,
    );
  });

  it("quotes the customer's text and shows each event's recorded instant", () => {
    const [first] = cards(found(ALICIA_TRACE));
    expect(first.querySelector(".trace-detail q")?.textContent).toBe(MESSAGE.text);
    expect(first.querySelector("time")?.getAttribute("dateTime")).toBe(MESSAGE.created_at);
  });

  it("says in text which event caused each one, and nothing for an event with no cause", () => {
    expect(cards(found(ALICIA_TRACE)).map((card) => text(card.querySelector(".trace-cause")) ?? null)).toEqual([
      null,
      es.trace.causedBy(1),
      es.trace.causedBy(2),
      es.trace.causedBy(3),
      es.trace.causedBy(3),
      es.trace.causedBy(3),
    ]);
  });

  it("draws one hidden connector per link", () => {
    const links = found(ALICIA_TRACE).querySelector(".trace-links");
    expect(links?.getAttribute("aria-hidden")).toBe("true");
    expect(links?.querySelectorAll("path")).toHaveLength(5);
  });

  it("shows the policy, the rules it evaluated, and the facts behind the decision", () => {
    const analysis = found(ALICIA_TRACE).querySelector(".trace-analysis");
    expect(text(analysis?.querySelector(".caption"))).toBe(`${es.trace.policy} alba-credit-v1`);
    expect([...(analysis?.querySelectorAll(".trace-rules li") ?? [])].map((row) => text(row))).toEqual([
      "R01 passed customer_status=Active",
      "R02 passed max_days_past_due=0",
      "R03 passed max_days_past_due=0",
      "R09 passed holds_product=false",
      "R04 passed credit_score=615",
      "R06 passed income_local=4707334.28 declared_income=null income_currency=COP",
      "R05 REFER credit_score=615",
    ]);
    const table = analysis?.querySelector(".trace-facts");
    expect([...(table?.querySelectorAll("tr") ?? [])].map((row) => [...row.children].map((cell) => text(cell)))).toEqual([
      [es.trace.columns.name, es.trace.columns.value, es.trace.columns.source, es.trace.columns.asOf],
      ["credit_score", "615", "customer_credit_profile.credit_score", "2026-06-17"],
      ["income_local", "4707334.28", "customer_credit_profile.income_local", "2026-06-17"],
      ["income_currency", "COP", "customer_credit_profile.income_currency", "2026-06-17"],
      ["income_usd", "1167.41890144", "customer_credit_profile.income_usd", "2026-06-17"],
    ]);
  });

  it("ends with a message written while a person has the case, with no classified turn after it", () => {
    const page = found({ ...ALICIA_TRACE, events: [...ALICIA_TRACE.events, STILL_WAITING] });
    const names = cards(page).map((card) => text(card.querySelector(".trace-name")));
    expect(names.at(-1)).toBe("conversation.message_received");
    expect(text(cards(page).at(-1)?.querySelector(".trace-detail"))).toBe("¿ya revisaron mi caso?");
    expect(names).not.toContain("conversation.turn_classified");
  });

  it("draws nothing for a cause outside the list, and logs it", () => {
    const logged = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const page = found({ ...ALICIA_TRACE, events: [STARTED] });
    expect(page.querySelector(".trace-cause")).toBeNull();
    expect(page.querySelector(".trace-links")).toBeNull();
    expect(logged).toHaveBeenCalledWith(
      `trace of ${ALICIA_TRACE.process_id}: event ${STARTED.id} names cause ${MESSAGE.id}, which is not in it`,
    );
  });
});

describe("the trace screen while it loads or fails", () => {
  it("says an unknown case does not exist and leads back to the queue", () => {
    const page = render({ status: "ready", data: { kind: "unknown" } });
    expect(text(page.querySelector(".heading"))).toBe(es.trace.unknown);
    expect(page.querySelector("a")?.getAttribute("href")).toBe("/consultant");
  });

  it("offers a retry when the read fails", () => {
    const page = render({ status: "error" });
    expect(text(page.querySelector("[role=alert] .heading"))).toBe(es.trace.loadFailed);
    expect(text(page.querySelector("button"))).toBe(es.retry);
  });

  it("shows placeholder cards while it loads", () => {
    const page = render({ status: "loading" });
    expect(page.querySelectorAll(".trace-slot")).toHaveLength(4);
    expect(cards(page)).toEqual([]);
  });
});
