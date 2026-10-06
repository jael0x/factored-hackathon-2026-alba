import { act, type ReactNode } from "react";
import { createRoot } from "react-dom/client";

declare global {
  var IS_REACT_ACT_ENVIRONMENT: boolean | undefined;
}

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

// Renders into a detached jsdom element, so a test reads what the browser would show, effects included.
export function renderForTest(element: ReactNode): HTMLElement {
  const container = document.createElement("div");
  act(() => createRoot(container).render(element));
  return container;
}
