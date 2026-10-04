import { useSyncExternalStore } from "react";

import type { components } from "../api/schema";
import { isRole } from "../routes";

export type Session = components["schemas"]["Session"];

export type SessionState =
  | { status: "signed_out" }
  | { status: "active"; session: Session }
  | { status: "ended" };

const STORAGE_KEY = "alba.session";

const listeners = new Set<() => void>();
let state: SessionState = readStored();

function readStored(): SessionState {
  const raw = window.sessionStorage.getItem(STORAGE_KEY);
  if (raw === null) {
    return { status: "signed_out" };
  }
  const parsed: unknown = JSON.parse(raw);
  if (!isSession(parsed)) {
    window.sessionStorage.removeItem(STORAGE_KEY);
    return { status: "signed_out" };
  }
  return { status: "active", session: parsed };
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
  window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  publish({ status: "active", session });
}

export function signOut(): void {
  window.sessionStorage.removeItem(STORAGE_KEY);
  publish({ status: "signed_out" });
}

export function endExpiredSession(): void {
  window.sessionStorage.removeItem(STORAGE_KEY);
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
