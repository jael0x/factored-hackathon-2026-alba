import { describe, expect, it } from "vitest";

import { codeFrom, type DemoMailbox } from "./demoCode";

const SINCE = Date.parse("2026-10-05T10:00:00Z");
const NEWEST: DemoMailbox = { kind: "newest" };
const CESAR: DemoMailbox = {
  kind: "sentTo",
  address: "Cesar.Rojas@alba.example",
};

type Listed = { Created: string; Snippet: string; To?: { Address: string }[] };

function listing(...messages: Listed[]) {
  return { messages };
}

describe("the demo code", () => {
  it("is the newest code written after the request", () => {
    const mail = listing(
      {
        Created: "2026-10-05T10:00:02Z",
        Snippet: "Tu código de Alba es 481206. Vale 10 minutos",
      },
      {
        Created: "2026-10-05T10:00:01Z",
        Snippet: "Tu código de Alba es 111111. Vale 10 minutos",
      },
    );
    expect(codeFrom(mail, SINCE, NEWEST)).toBe("481206");
  });

  it("ignores a code sent before the request", () => {
    const mail = listing({
      Created: "2026-10-05T09:59:00Z",
      Snippet: "Seu código Alba é 222222.",
    });
    expect(codeFrom(mail, SINCE, NEWEST)).toBeNull();
  });

  it("for a consultant, is the newest code sent to the address typed, in any letter case", () => {
    const mail = listing(
      {
        Created: "2026-10-05T10:00:03Z",
        Snippet: "Tu código de Alba es 333333.",
        To: [{ Address: "juan@alba.example" }],
      },
      {
        Created: "2026-10-05T10:00:02Z",
        Snippet: "Tu código de Alba es 444444.",
        To: [{ Address: "cesar.rojas@alba.example" }],
      },
    );
    expect(codeFrom(mail, SINCE, CESAR)).toBe("444444");
  });

  it("for a consultant, ignores a code with no recipient", () => {
    const mail = listing({
      Created: "2026-10-05T10:00:02Z",
      Snippet: "Tu código de Alba es 555555.",
    });
    expect(codeFrom(mail, SINCE, CESAR)).toBeNull();
  });

  it("reads nothing from an answer that is not a Mailpit listing", () => {
    expect(codeFrom(null, SINCE, NEWEST)).toBeNull();
    expect(codeFrom({ messages: [null, { Created: 1, To: [null, { Address: 7 }] }] }, SINCE, NEWEST)).toBeNull();
  });
});
