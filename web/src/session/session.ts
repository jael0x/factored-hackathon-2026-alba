import { useSyncExternalStore } from "react";

import type { components } from "../api/schema";
import { isRole } from "../routes";
import { tabItems } from "../storage";

export type Session = components["schemas"]["Session"];

export type SessionState =
  | { status: "signed_out" }
  | { status: "active"; session: Session }
  | { status: "ended" };

const STORAGE_KEY = "alba.session";

const listeners = new Set<() => void>();
let state: SessionState = readStored();

function readStored(): SessionState {
  const raw = tabItems.read(STORAGE_KEY);
  if (raw === null) {
    return { status: "signed_out" };
  }
  const parsed = parseJson(raw);
  if (!isSession(parsed)) {
    tabItems.remove(STORAGE_KEY);
    return { status: "signed_out" };
  }
  return { status: "active", session: parsed };
}

function parseJson(raw: string): unknown {
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function isSession(value: unknown): value is Session {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.token === "string" &&
    typeof candidate.sub === "string" &&
    isRole(candidate.role)
  );
}

function publish(next: SessionState): void {
  state = next;
  listeners.forEach((listener) => listener());
}

export function startSession(session: Session): void {
  tabItems.write(STORAGE_KEY, JSON.stringify(session));
  publish({ status: "active", session });
}

export function signOut(): void {
  tabItems.remove(STORAGE_KEY);
  publish({ status: "signed_out" });
}

export function endExpiredSession(): void {
  tabItems.remove(STORAGE_KEY);
  publish({ status: "ended" });
}

export function currentToken(): string | null {
  return state.status === "active" ? state.session.token : null;
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useSession(): SessionState {
  return useSyncExternalStore(subscribe, () => state);
}
