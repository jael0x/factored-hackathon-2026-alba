import type { ReactNode } from "react";

import type { components } from "../api/schema";
import { ASK_ABOUT } from "../products";

type ProductKey = components["schemas"]["ProductKey"];

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

export function ProductRows() {
  return (
    <section className="sheet glass" aria-labelledby="ask-about">
      <h2 id="ask-about" className="heading">
        Preguntar por
      </h2>
      {ASK_ABOUT.map(({ key, label }) => (
        <button key={key} type="button" className="chev" disabled>
          <span className="tile">
            <svg className="i" viewBox="0 0 24 24" aria-hidden="true">
              {ICONS[key]}
            </svg>
          </span>
          <span className="grow">{label}</span>
          <svg className="i" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M9 6l6 6-6 6" />
          </svg>
        </button>
      ))}
    </section>
  );
}
