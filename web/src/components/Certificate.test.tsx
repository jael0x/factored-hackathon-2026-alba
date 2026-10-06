import { describe, expect, it } from "vitest";

import type { components } from "../api/schema";
import { es } from "../i18n/es";
import { renderForTest } from "../renderForTest";
import { Certificate } from "./Certificate";

type CertificateData = components["schemas"]["Certificate"];

const BY_A_PERSON: CertificateData = {
  event_id: "d1",
  decided_by: "consultant",
  locale: "es",
  outcome: "PREQUALIFIED",
  body: "Una persona del banco revisó tu solicitud.",
  product: "credit_card",
  income_local: null,
  income_currency: null,
  income_usd: null,
  as_of: null,
};

function reviewedLine(certificate: CertificateData): string | null | undefined {
  return renderForTest(<Certificate certificate={certificate} appeal={null} />).querySelector(".reviewed")?.textContent;
}

describe("the certificate", () => {
  it("says a person reviewed it when the consultant decided", () => {
    expect(reviewedLine(BY_A_PERSON)).toBe(es.certificate.reviewed);
  });

  it("does not say so when the policy decided", () => {
    expect(reviewedLine({ ...BY_A_PERSON, decided_by: "policy" })).toBeUndefined();
  });
});
