import { afterEach, describe, expect, it, vi } from "vitest";

import type { Session } from "./session";

const JUAN: Session = { token: "header.payload.signature", sub: "CLI-JUAN", role: "customer" };

function blockStorage(): void {
  vi.spyOn(window, "sessionStorage", "get").mockImplementation(() => {
    throw new DOMException("The operation is insecure.", "SecurityError");
  });
}

async function openApp(): Promise<typeof import("./session")> {
  vi.resetModules();
  return import("./session");
}

afterEach(() => {
  vi.restoreAllMocks();
  window.sessionStorage.clear();
});

describe("the session", () => {
  it("comes back after a reload", async () => {
    const app = await openApp();
    app.startSession(JUAN);
    const reloaded = await openApp();
    expect(reloaded.currentToken()).toBe(JUAN.token);
  });

  it("is gone after a reload once the customer signs out", async () => {
    const app = await openApp();
    app.startSession(JUAN);
    app.signOut();
    expect(app.currentToken()).toBeNull();
    expect((await openApp()).currentToken()).toBeNull();
  });

  it("is gone after a reload once it expired", async () => {
    const app = await openApp();
    app.startSession(JUAN);
    app.endExpiredSession();
    expect(app.currentToken()).toBeNull();
    expect((await openApp()).currentToken()).toBeNull();
  });

  it("clears a stored value that is not JSON and opens signed out", async () => {
    window.sessionStorage.setItem("alba.session", "{");
    const app = await openApp();
    expect(app.currentToken()).toBeNull();
    expect(window.sessionStorage.getItem("alba.session")).toBeNull();
  });

  it("clears a stored session with a role the app does not know", async () => {
    window.sessionStorage.setItem("alba.session", JSON.stringify({ ...JUAN, role: "admin" }));
    const app = await openApp();
    expect(app.currentToken()).toBeNull();
    expect(window.sessionStorage.getItem("alba.session")).toBeNull();
  });

  it("works for the tab when storage is blocked, and is lost on reload", async () => {
    blockStorage();
    const app = await openApp();
    expect(app.currentToken()).toBeNull();
    app.startSession(JUAN);
    expect(app.currentToken()).toBe(JUAN.token);
    expect((await openApp()).currentToken()).toBeNull();
  });
});
