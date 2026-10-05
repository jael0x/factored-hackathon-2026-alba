// With DEMO_LOGIN on, the login page reads the code back from the local mail catcher, as a tester would in its
// inbox (PLAN.md D25). The API never returns a code; this only reads the email it sent to Mailpit.
const MAILPIT_MESSAGES = "/mailpit/api/v1/messages?limit=5";
const CODE = /\b\d{6}\b/;
const ATTEMPTS = 10;
const ATTEMPT_DELAY_MS = 500;

// Mailpit lists the newest message first; the code is the newest one written after the request.
export function codeFrom(listing: unknown, since: number): string | null {
  if (typeof listing !== "object" || listing === null || !("messages" in listing) || !Array.isArray(listing.messages)) {
    return null;
  }
  for (const message of listing.messages as unknown[]) {
    if (typeof message !== "object" || message === null) {
      continue;
    }
    const created = "Created" in message && typeof message.Created === "string" ? Date.parse(message.Created) : NaN;
    const snippet = "Snippet" in message && typeof message.Snippet === "string" ? message.Snippet : "";
    const code = snippet.match(CODE);
    if (created >= since && code) {
      return code[0];
    }
  }
  return null;
}

export async function readDemoCode(since: number): Promise<string | null> {
  for (let attempt = 0; attempt < ATTEMPTS; attempt += 1) {
    const listing = await fetch(MAILPIT_MESSAGES)
      .then((response) => (response.ok ? response.json() : null))
      .catch(() => null);
    const code = codeFrom(listing, since);
    if (code !== null) {
      return code;
    }
    await new Promise((resolve) => window.setTimeout(resolve, ATTEMPT_DELAY_MS));
  }
  return null;
}
