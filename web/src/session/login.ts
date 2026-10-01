import type { components } from "../api/schema";
import type { Session } from "./session";

type CodeRequested = components["schemas"]["CodeRequested"];

export type SessionAnswer = { status: "opened"; session: Session } | { status: "rejected" } | { status: "unreachable" };

export async function codeExpiry(request: Promise<{ data?: CodeRequested }>): Promise<number | null> {
  const { data } = await request.catch(() => ({ data: undefined }));
  return data ? data.expires_in_seconds : null;
}

export async function sessionAnswer(request: Promise<{ data?: Session; response: Response }>): Promise<SessionAnswer> {
  const result = await request.catch(() => null);
  if (result?.data) {
    return { status: "opened", session: result.data };
  }
  return result?.response.status === 401 ? { status: "rejected" } : { status: "unreachable" };
}
