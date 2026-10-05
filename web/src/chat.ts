import type { components } from "./api/schema";
import type { Locale } from "./i18n/locale";

type MessageAuthor = components["schemas"]["MessageAuthor"];
type ProcessState = components["schemas"]["ProcessState"];
type ProductKey = components["schemas"]["ProductKey"];
type CaseSummary = components["schemas"]["CaseSummary"];

// One send: the same id and locale go out again on a retry, so the API answers it as the same message.
// A start from the home names its product (the consent given in the dialog); every other send goes to its case.
export type PendingSend = { text: string; clientMessageId: string; locale: Locale; product?: ProductKey };

// What a product row on the home does: start a case, continue the open one, or show the ended one's result.
export type RowAction = { kind: "start" } | { kind: "continue" | "result"; processId: string };

export type Bubble = { side: "me" | "alba"; surface: "tinted" | "glass" | "solid" };

// DESIGN.md "Messages": the surface follows messages.author.
const BUBBLES: Record<MessageAuthor, Bubble> = {
  customer: { side: "me", surface: "tinted" },
  assistant: { side: "alba", surface: "glass" },
  template: { side: "alba", surface: "solid" },
};

const AI_ACTIVE: ProcessState = "ai_active";

export function newSend(text: string, locale: Locale, product?: ProductKey): PendingSend {
  return { text, clientMessageId: crypto.randomUUID(), locale, product };
}

// GET /cases lists newest first, so the first case of a product is the one its row stands for.
export function rowAction(cases: CaseSummary[], product: ProductKey): RowAction {
  const latest = cases.find((item) => item.product === product);
  if (latest === undefined) {
    return { kind: "start" };
  }
  return { kind: latest.state === "ended" ? "result" : "continue", processId: latest.process_id };
}

export function bubbleOf(author: MessageAuthor): Bubble {
  return BUBBLES[author];
}

// The typing indicator lasts as long as a send waits, and only while the assistant still has the case.
export function showsTyping(sending: boolean, state: ProcessState | null): boolean {
  return sending && (state === null || state === AI_ACTIVE);
}
