import { useState } from "react";

import { api } from "../api/client";
import type { components } from "../api/schema";
import { CodeStep, type CodeSent } from "../components/CodeStep";
import type { DemoSource } from "../components/DemoSearch";
import { DemoSearchPopover } from "../components/DemoSearchPopover";
import { IdentityForm } from "../components/IdentityForm";
import { LoginShell } from "../components/LoginShell";
import { TextField } from "../components/TextField";
import { fullName, lastFour } from "../format";
import type { Messages } from "../i18n/es";
import { useLocale, type Locale } from "../i18n/locale";
import { useMessages } from "../i18n/messages";
import { HOME_PATH } from "../routes";
import { codeExpiry, sessionAnswer } from "../session/login";

type CustomerHit = components["schemas"]["CustomerSearchHit"];

type Sent = CodeSent & { documentNumber: string };

const searchCustomers = async (q: string) => {
  const { data } = await api.GET("/customers/search", { params: { query: { q } } }).catch(() => ({ data: undefined }));
  return data ? data.customers : null;
};

const pickRandomCustomer = async () => {
  const { data } = await api
    .GET("/customers/search", { params: { query: { random: true } } })
    .catch(() => ({ data: undefined }));
  return data?.customers[0] ?? null;
};

const customerDemo = (copy: Messages["demo"]["customers"]): DemoSource<CustomerHit> => ({
  heading: copy.heading,
  help: copy.help,
  queryLabel: copy.queryLabel,
  search: searchCustomers,
  pickRandom: pickRandomCustomer,
  key: (hit) => hit.customer_id,
  render: (hit) => (
    <>
      <span className="name">{fullName(hit)}</span>
      <br />
      <span className="caption muted">
        {hit.country} · {copy.document}{" "}
        <span aria-label={`${copy.endingIn} ${lastFour(hit.document_number)}`}>••••{lastFour(hit.document_number)}</span>
      </span>
    </>
  ),
});

const requestCode = (documentNumber: string, locale: Locale) =>
  codeExpiry(api.POST("/session/code", { body: { document_number: documentNumber, locale } }));

const openSession = (documentNumber: string, code: string) =>
  sessionAnswer(api.POST("/session", { body: { document_number: documentNumber, code } }));

export function Login() {
  const [documentNumber, setDocumentNumber] = useState("");
  const [sent, setSent] = useState<Sent | null>(null);
  const locale = useLocale();
  const t = useMessages();
  const copy = t.login.customer;
  const trimmed = documentNumber.trim();

  const pick = (hit: CustomerHit) => {
    setDocumentNumber(hit.document_number);
    setSent(null);
  };

  return (
    <LoginShell
      role="customer"
      title={copy.title}
      lede={copy.lede}
      notice={copy.notice}
      panelTitle={sent ? t.login.yourCode : copy.panelTitle}
      demo={
        <DemoSearchPopover
          source={customerDemo(t.demo.customers)}
          isSelected={(hit) => hit.document_number === documentNumber}
          onPick={pick}
        />
      }
    >
      {sent ? (
        <CodeStep
          identity={[{ label: copy.document, value: sent.documentNumber }]}
          sent={sent}
          changeLabel={copy.change}
          home={HOME_PATH.customer}
          requestCode={() => requestCode(sent.documentNumber, locale)}
          openSession={(code) => openSession(sent.documentNumber, code)}
          onResent={(next) => setSent({ ...sent, ...next })}
          onChangeIdentity={() => setSent(null)}
        />
      ) : (
        <IdentityForm
          ready={trimmed !== ""}
          requestCode={() => requestCode(trimmed, locale)}
          onSent={(expiresInSeconds) => setSent({ documentNumber: trimmed, expiresInSeconds, resent: false })}
        >
          <TextField
            label={copy.documentNumber}
            autoComplete="off"
            value={documentNumber}
            onChange={setDocumentNumber}
          />
        </IdentityForm>
      )}
    </LoginShell>
  );
}
