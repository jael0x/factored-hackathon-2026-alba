// With DEMO_LOGIN on, the login page reads the code back from the local mail catcher, as a tester would in its
// inbox (PLAN.md D25). The API never returns a code; this only reads the email it sent to Mailpit.
const MAILPIT_MESSAGES = "/mailpit/api/v1/messages?limit=5";
const CODE = /\b\d{6}\b/;
const ATTEMPTS = 10;
const ATTEMPT_DELAY_MS = 500;

// A consultant types the address the code goes to. A customer types a document number, and the screen never knows
// the address, so it takes the newest code sent after the request: right on a local stack with one tester.
export type DemoMailbox = { kind: "newest" } | { kind: "sentTo"; address: string };

type Listed = { created: number; snippet: string; to: string[] };

// Mailpit lists the newest message first.
export function codeFrom(listing: unknown, since: number, mailbox: DemoMailbox): string | null {
  if (typeof listing !== "object" || listing === null || !("messages" in listing) || !Array.isArray(listing.messages)) {
    return null;
  }
  for (const message of (listing.messages as unknown[]).map(listedOf)) {
    const code = message?.snippet.match(CODE);
    if (message && code && message.created >= since && reaches(message, mailbox)) {
      return code[0];
    }
  }
  return null;
}

function listedOf(message: unknown): Listed | null {
  if (typeof message !== "object" || message === null) {
    return null;
  }
  const created = "Created" in message && typeof message.Created === "string" ? Date.parse(message.Created) : NaN;
  const snippet = "Snippet" in message && typeof message.Snippet === "string" ? message.Snippet : "";
  const to = "To" in message && Array.isArray(message.To) ? (message.To as unknown[]).map(addressOf) : [];
  return {
    created,
    snippet,
    to: to.filter((address): address is string => address !== null),
  };
}

function addressOf(recipient: unknown): string | null {
  if (typeof recipient !== "object" || recipient === null || !("Address" in recipient)) {
    return null;
  }
  return typeof recipient.Address === "string" ? recipient.Address.toLowerCase() : null;
}

function reaches(message: Listed, mailbox: DemoMailbox): boolean {
  return mailbox.kind === "newest" || message.to.includes(mailbox.address.toLowerCase());
}

export async function readDemoCode(since: number, mailbox: DemoMailbox): Promise<string | null> {
  for (let attempt = 0; attempt < ATTEMPTS; attempt += 1) {
    const listing = await fetch(MAILPIT_MESSAGES)
      .then((response) => (response.ok ? response.json() : null))
      .catch(() => null);
    const code = codeFrom(listing, since, mailbox);
    if (code !== null) {
      return code;
    }
    await new Promise((resolve) => window.setTimeout(resolve, ATTEMPT_DELAY_MS));
  }
  return null;
}
