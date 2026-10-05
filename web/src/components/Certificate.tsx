import { useId } from "react";

import type { components } from "../api/schema";
import { PREQUALIFIED } from "../chat";
import { formatAmount, formatDate } from "../format";
import { useMessages } from "../i18n/messages";

type CertificateData = components["schemas"]["Certificate"];

// DESIGN.md "Certificate": the hero, its outcome tag, the product, the template paragraph, and the income it read.
type Appeal = { busy: boolean; failed: boolean; onAppeal: () => void };

export function Certificate({ certificate, appeal }: { certificate: CertificateData; appeal: Appeal | null }) {
  const t = useMessages();
  const titleId = useId();
  const { outcome, product, body, income_local, income_currency, income_usd, as_of, locale } = certificate;
  return (
    <section
      className={`certificate hero enter ${outcome === PREQUALIFIED ? "yes" : "no"}`}
      aria-labelledby={titleId}
      lang={locale}
    >
      <span className="tag">{t.certificate.tag[outcome]}</span>
      {product && (
        <h2 className="title" id={titleId}>
          {t.products.askAbout[product]}
        </h2>
      )}
      <p>{body}</p>
      {income_local !== null && income_currency !== null && (
        <>
          <p className="kicker">{t.certificate.facts}</p>
          <dl className="facts">
            <div>
              <dt>{t.certificate.income}</dt>
              <dd>
                {formatAmount(income_local)} {income_currency}
              </dd>
            </div>
            {income_usd !== null && (
              <div>
                <dt>{t.certificate.incomeUsd}</dt>
                <dd>
                  {formatAmount(income_usd)} USD
                  {as_of !== null && (
                    <span className="caption"> {t.certificate.rateOn(formatDate(as_of, locale))}</span>
                  )}
                </dd>
              </div>
            )}
          </dl>
        </>
      )}
      {appeal && (
        <div className="certificate-actions">
          <button type="button" className="btn hero-secondary" onClick={appeal.onAppeal} disabled={appeal.busy}>
            {t.certificate.appeal}
          </button>
          {appeal.failed && (
            <p className="caption" role="alert">
              {t.certificate.appealFailed}
            </p>
          )}
        </div>
      )}
    </section>
  );
}
