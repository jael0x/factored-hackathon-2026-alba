import * as ts from "typescript";
import { afterEach, describe, expect, it, vi } from "vitest";

import { browserItems, tabItems } from "./storage";

const STORAGE_NAMES = new Set(["localStorage", "sessionStorage"]);

const SOURCES = import.meta.glob<string>(["./**/*.{ts,tsx}", "!./**/*.test.{ts,tsx}"], {
  query: "?raw",
  import: "default",
  eager: true,
});

type StorageUse = { at: string; name: string };

function storageUses(path: string, text: string): StorageUse[] {
  const kind = path.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS;
  const file = ts.createSourceFile(path, text, ts.ScriptTarget.Latest, true, kind);
  const found: StorageUse[] = [];
  const visit = (node: ts.Node): void => {
    if ((ts.isIdentifier(node) || ts.isStringLiteralLike(node)) && STORAGE_NAMES.has(node.text)) {
      const line = file.getLineAndCharacterOfPosition(node.getStart()).line + 1;
      found.push({ at: `${path}:${line}`, name: node.text });
    }
    ts.forEachChild(node, visit);
  };
  visit(file);
  return found;
}

function block(area: "localStorage" | "sessionStorage"): void {
  vi.spyOn(window, area, "get").mockImplementation(() => {
    throw new DOMException("The operation is insecure.", "SecurityError");
  });
}

afterEach(() => {
  vi.restoreAllMocks();
  window.localStorage.clear();
  window.sessionStorage.clear();
});

describe("browser storage", () => {
  it("is touched only by storage.ts", () => {
    const outside = Object.entries(SOURCES)
      .filter(([path]) => path !== "./storage.ts")
      .flatMap(([path, text]) => storageUses(path, text))
      .map((use) => `${use.at} ${use.name}`);
    expect(outside).toEqual([]);
  });

  it("is found by the scan where storage.ts touches it", () => {
    expect(Object.keys(SOURCES)).toEqual(expect.arrayContaining(["./storage.ts", "./i18n/locale.ts"]));
    const names = storageUses("./storage.ts", SOURCES["./storage.ts"]).map((use) => use.name);
    expect(names).toEqual(["localStorage", "sessionStorage"]);
  });

  it("keeps each area apart", () => {
    browserItems.write("alba.test", "browser");
    tabItems.write("alba.test", "tab");
    expect(window.localStorage.getItem("alba.test")).toBe("browser");
    expect(window.sessionStorage.getItem("alba.test")).toBe("tab");
    browserItems.remove("alba.test");
    expect(browserItems.read("alba.test")).toBeNull();
    expect(tabItems.read("alba.test")).toBe("tab");
  });

  it("reads a blocked area as empty and drops writes without throwing", () => {
    window.localStorage.setItem("alba.test", "kept");
    block("localStorage");
    expect(browserItems.read("alba.test")).toBeNull();
    expect(() => browserItems.write("alba.test", "lost")).not.toThrow();
    expect(() => browserItems.remove("alba.test")).not.toThrow();
    vi.restoreAllMocks();
    expect(window.localStorage.getItem("alba.test")).toBe("kept");
  });

  it("drops a write to a full area without throwing", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("The quota has been exceeded.", "QuotaExceededError");
    });
    expect(() => tabItems.write("alba.test", "too much")).not.toThrow();
    vi.restoreAllMocks();
    expect(window.sessionStorage.getItem("alba.test")).toBeNull();
  });
});
