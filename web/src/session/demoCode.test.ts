import { describe, expect, it } from "vitest";

import { codeFrom } from "./demoCode";

const SINCE = Date.parse("2026-10-05T10:00:00Z");

function listing(...messages: { Created: string; Snippet: string }[]) {
  return { messages };
}

describe("the demo code", () => {
  it("is the newest code written after the request", () => {
    const mail = listing(
      { Created: "2026-10-05T10:00:02Z", Snippet: "Tu código de Alba es 481206. Vale 10 minutos" },
      { Created: "2026-10-05T10:00:01Z", Snippet: "Tu código de Alba es 111111. Vale 10 minutos" },
    );
    expect(codeFrom(mail, SINCE)).toBe("481206");
  });

  it("ignores a code sent before the request", () => {
    expect(
      codeFrom(listing({ Created: "2026-10-05T09:59:00Z", Snippet: "Seu código Alba é 222222." }), SINCE),
    ).toBeNull();
  });

  it("reads nothing from an answer that is not a Mailpit listing", () => {
    expect(codeFrom(null, SINCE)).toBeNull();
    expect(codeFrom({ messages: [null, { Created: 1 }] }, SINCE)).toBeNull();
  });
});
