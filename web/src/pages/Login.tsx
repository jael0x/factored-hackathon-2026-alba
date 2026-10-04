import { useState } from "react";

import { api } from "../api/client";
import type { components } from "../api/schema";
import type { DemoSource } from "../components/DemoSearch";
import { DemoSearchPopover } from "../components/DemoSearchPopover";
import { LoginShell } from "../components/LoginShell";
import { LoginSteps, type SentTo } from "../components/LoginSteps";
import { TextField } from "../components/TextField";
import { fullName, lastFour } from "../format";
import type { Messages } from "../i18n/es";
import type { Locale } from "../i18n/locale";
import { useMessages } from "../i18n/messages";
import { codeExpiry, sessionAnswer } from "../session/login";

type CustomerHit = components["schemas"]["CustomerSearchHit"];

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
  const [sent, setSent] = useState<SentTo<string> | null>(null);
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
      codeSent={sent !== null}
      demo={
        <DemoSearchPopover
          source={customerDemo(t.demo.customers)}
          isSelected={(hit) => hit.document_number === documentNumber}
          onPick={pick}
        />
      }
    >
      <LoginSteps
        role="customer"
        typed={trimmed === "" ? null : trimmed}
        sent={sent}
        onSentChange={setSent}
        identityRows={(number) => [{ label: copy.document, value: number }]}
        requestCode={requestCode}
        openSession={openSession}
      >
        <TextField label={copy.documentNumber} value={documentNumber} onChange={setDocumentNumber} />
      </LoginSteps>
    </LoginShell>
  );
}
