import { describe, expect, it } from "vitest";

import { bubbleOf, newSend, rowAction, showsTyping } from "./chat";

describe("the chat", () => {
  it("puts the customer on the right and Alba on the left, a template on white", () => {
    expect(bubbleOf("customer")).toEqual({ side: "me", surface: "tinted" });
    expect(bubbleOf("assistant")).toEqual({ side: "alba", surface: "glass" });
    expect(bubbleOf("template")).toEqual({ side: "alba", surface: "solid" });
  });

  it("gives every send its own id and keeps the language it was sent in", () => {
    const first = newSend("Quiero una tarjeta de crédito", "es");
    const second = newSend("Quiero una tarjeta de crédito", "es");
    expect(first.clientMessageId).not.toBe(second.clientMessageId);
    expect(first).toMatchObject({ text: "Quiero una tarjeta de crédito", locale: "es" });
  });

  it("shows the typing indicator only while a send waits on a case the assistant has", () => {
    expect(showsTyping(true, null)).toBe(true);
    expect(showsTyping(true, "ai_active")).toBe(true);
    expect(showsTyping(true, "human_active")).toBe(false);
    expect(showsTyping(false, "ai_active")).toBe(false);
  });

  it("starts a product with no case, continues an open one, and shows the result of an ended one", () => {
    const card = (state: "ai_active" | "human_active" | "ended", id: string) => ({
      process_id: id,
      product: "credit_card" as const,
      state,
      end_reason: null,
      locale: "es" as const,
    });
    expect(rowAction([], "credit_card")).toEqual({ kind: "start" });
    expect(rowAction([card("ai_active", "a")], "credit_card")).toEqual({ kind: "continue", processId: "a" });
    expect(rowAction([card("human_active", "b")], "credit_card")).toEqual({ kind: "continue", processId: "b" });
    expect(rowAction([card("ended", "c"), card("ended", "d")], "credit_card")).toEqual({
      kind: "result",
      processId: "c",
    });
    expect(rowAction([card("ai_active", "a")], "personal_loan")).toEqual({ kind: "start" });
  });

  it("names the product on a start and nothing on a message in a case", () => {
    expect(newSend("Quiero una tarjeta de crédito", "es", "credit_card").product).toBe("credit_card");
    expect(newSend("gano 45,000 pesos al mes", "es").product).toBeUndefined();
  });
});
