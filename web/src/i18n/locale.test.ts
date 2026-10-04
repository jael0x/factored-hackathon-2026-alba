import { afterEach, describe, expect, it, vi } from "vitest";

function browserPrefers(...languages: string[]): void {
  vi.spyOn(window.navigator, "languages", "get").mockReturnValue(languages);
}

function blockStorage(): void {
  vi.spyOn(window, "localStorage", "get").mockImplementation(() => {
    throw new DOMException("The operation is insecure.", "SecurityError");
  });
}

async function openPage(): Promise<typeof import("./locale")> {
  vi.resetModules();
  return import("./locale");
}

afterEach(() => {
  vi.restoreAllMocks();
  window.localStorage.clear();
});

describe("the language switch", () => {
  it("follows the browser's language on a first visit", async () => {
    browserPrefers("pt-BR", "en-US");
    await openPage();
    expect(document.documentElement.lang).toBe("pt");
  });

  it("gives Spanish to a browser in another language", async () => {
    browserPrefers("en-US", "fr");
    await openPage();
    expect(document.documentElement.lang).toBe("es");
  });

  it("keeps the chosen language for the next visit", async () => {
    browserPrefers("es-MX");
    const page = await openPage();
    page.setLocale("pt");
    await openPage();
    expect(document.documentElement.lang).toBe("pt");
    expect(window.localStorage.getItem("alba.locale")).toBe("pt");
  });

  it("ignores a stored value that is not one of the two languages", async () => {
    browserPrefers("pt-BR");
    window.localStorage.setItem("alba.locale", "en");
    await openPage();
    expect(document.documentElement.lang).toBe("pt");
  });

  it("opens in the browser's language when storage is blocked", async () => {
    browserPrefers("pt-PT");
    blockStorage();
    await openPage();
    expect(document.documentElement.lang).toBe("pt");
  });

  it("still switches for the tab when storage is blocked", async () => {
    browserPrefers("es-AR");
    blockStorage();
    const page = await openPage();
    page.setLocale("pt");
    expect(document.documentElement.lang).toBe("pt");
    await openPage();
    expect(document.documentElement.lang).toBe("es");
  });
});
