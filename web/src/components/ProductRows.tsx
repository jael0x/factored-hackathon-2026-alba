import type { ReactNode } from "react";

import type { components } from "../api/schema";
import { rowAction } from "../chat";
import { useMessages } from "../i18n/messages";
import { ASK_ABOUT } from "../products";

type ProductKey = components["schemas"]["ProductKey"];
type CaseSummary = components["schemas"]["CaseSummary"];

const ICONS: Record<ProductKey, ReactNode> = {
  credit_card: (
    <>
      <rect x="3" y="5.5" width="18" height="13" rx="3" />
      <path d="M3 10h18M7 15h3" />
    </>
  ),
  personal_loan: (
    <>
      <rect x="3" y="6.5" width="18" height="11" rx="2.5" />
      <circle cx="12" cy="12" r="2.5" />
      <path d="M6.5 12h.01M17.5 12h.01" />
    </>
  ),
};

type ProductRowsProps = {
  cases: CaseSummary[];
  onStart: (key: ProductKey) => void;
  onOpen: (processId: string) => void;
};

// Each product has one row: it starts a case (after the dialog), continues the open one, or shows the result (D24).
export function ProductRows({ cases, onStart, onOpen }: ProductRowsProps) {
  const t = useMessages();
  return (
    <section className="sheet glass" aria-labelledby="ask-about">
      <h2 id="ask-about" className="heading">
        {t.home.askAbout}
      </h2>
      {ASK_ABOUT.map((key) => {
        const action = rowAction(cases, key);
        const status =
          action.kind === "continue" ? t.home.continueCase : action.kind === "result" ? t.home.seeResult : null;
        return (
          <button
            key={key}
            type="button"
            className="chev"
            onClick={() => (action.kind === "start" ? onStart(key) : onOpen(action.processId))}
          >
            <span className="tile">
              <svg className="i" viewBox="0 0 24 24" aria-hidden="true">
                {ICONS[key]}
              </svg>
            </span>
            <span className="grow">
              {t.products.askAbout[key]}
              {status && <span className="caption muted row-status">{status}</span>}
            </span>
            <svg className="i" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M9 6l6 6-6 6" />
            </svg>
          </button>
        );
      })}
    </section>
  );
}
