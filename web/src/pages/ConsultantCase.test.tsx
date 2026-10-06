import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";

import type { components } from "../api/schema";
import type { CloseAnswer } from "../consultant";
import { ALICIA, BEFORE_THE_POLICY, JULIANA } from "../consultant.fixtures";
import { es } from "../i18n/es";
import { renderForTest } from "../renderForTest";
import { ConsultantCaseView } from "./ConsultantCase";

type ConsultantCase = components["schemas"]["ConsultantCase"];

function render(packet: ConsultantCase, answer: CloseAnswer | null = null): HTMLElement {
  return renderForTest(
    <MemoryRouter>
      <ConsultantCaseView
        packet={packet}
        answer={answer}
        closing={false}
        onClose={() => Promise.resolve()}
        onRefresh={() => undefined}
      />
    </MemoryRouter>,
  );
}

const closeButtons = (page: HTMLElement) =>
  [...page.querySelectorAll(".packet button")].map((button) => button.textContent);

describe("the consultant's case", () => {
  it("has no field to write in and only the two close actions", () => {
    const page = render(ALICIA);
    expect(page.querySelectorAll("input, textarea, [contenteditable]")).toHaveLength(0);
    expect(closeButtons(page)).toEqual(["Precalificar", "No precalificar"]);
  });

  it("shows the customer's thread in her own language, as she wrote it", () => {
    const thread = render(ALICIA).querySelector(".convo .thread");
    expect(thread?.getAttribute("lang")).toBe("pt");
    expect([...(thread?.querySelectorAll(".bubble") ?? [])].map((bubble) => bubble.textContent)).toEqual(
      ALICIA.messages.map((line) => line.body),
    );
  });

  it.each([JULIANA, BEFORE_THE_POLICY])("offers no close on a case the policy left without a result", (packet) => {
    const page = render(packet);
    expect(closeButtons(page)).toEqual([]);
    expect(page.querySelector(".packet-note")?.textContent).toBe(es.consultant.notClosable);
  });

  it("offers no close while one is settling, and a way to read the case again", () => {
    const page = render(ALICIA, { kind: "pending" });
    expect(closeButtons(page)).toEqual([]);
    expect(page.querySelector(".close-notice")?.textContent).toBe(
      `${es.consultant.answers.pending}${es.consultant.refresh}`,
    );
  });
});
