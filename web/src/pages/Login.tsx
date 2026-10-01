import { useId, useState } from "react";

import { api } from "../api/client";
import type { components } from "../api/schema";
import { CodeStep, type CodeSent } from "../components/CodeStep";
import type { DemoSource } from "../components/DemoSearch";
import { DemoSearchPopover } from "../components/DemoSearchPopover";
import { IdentityForm } from "../components/IdentityForm";
import { LoginShell } from "../components/LoginShell";
import { fullName, lastFour } from "../format";
import { HOME_PATH } from "../routes";
import { codeExpiry, sessionAnswer } from "../session/login";

type CustomerHit = components["schemas"]["CustomerSearchHit"];

type Sent = CodeSent & { documentNumber: string };

const customerDemo: DemoSource<CustomerHit> = {
  heading: "Usuarios de prueba",
  help: "Solo en el demo. Elegir a alguien llena su documento y cierra este panel; el código igual llega por correo.",
  queryLabel: "Nombre, documento o número de cliente",
  search: async (q) => {
    const { data } = await api.GET("/customers/search", { params: { query: { q } } }).catch(() => ({ data: undefined }));
    return data ? data.customers : null;
  },
  pickRandom: async () => {
    const { data } = await api
      .GET("/customers/search", { params: { query: { random: true } } })
      .catch(() => ({ data: undefined }));
    return data?.customers[0] ?? null;
  },
  key: (hit) => hit.customer_id,
  render: (hit) => (
    <>
      <span className="name">{fullName(hit)}</span>
      <br />
      <span className="caption muted">
        {hit.country} · documento{" "}
        <span aria-label={`terminado en ${lastFour(hit.document_number)}`}>••••{lastFour(hit.document_number)}</span>
      </span>
    </>
  ),
};

const requestCode = (documentNumber: string) =>
  codeExpiry(api.POST("/session/code", { body: { document_number: documentNumber } }));

const openSession = (documentNumber: string, code: string) =>
  sessionAnswer(api.POST("/session", { body: { document_number: documentNumber, code } }));

export function Login() {
  const fieldId = useId();
  const [documentNumber, setDocumentNumber] = useState("");
  const [sent, setSent] = useState<Sent | null>(null);
  const trimmed = documentNumber.trim();

  const pick = (hit: CustomerHit) => {
    setDocumentNumber(hit.document_number);
    setSent(null);
  };

  return (
    <LoginShell
      role="customer"
      title="Entra a tu cuenta"
      lede="Escribe tu número de documento. Te enviaremos un código de un solo uso al correo registrado."
      notice="Si tu documento está registrado y tiene un correo asociado, te enviaremos un código. Si no te llega, acércate a una sucursal para registrar tu correo."
      panelTitle={sent ? "Tu código" : "Tu documento"}
      demo={
        <DemoSearchPopover
          source={customerDemo}
          isSelected={(hit) => hit.document_number === documentNumber}
          onPick={pick}
        />
      }
    >
      {sent ? (
        <CodeStep
          identity={[{ label: "Documento", value: sent.documentNumber }]}
          sent={sent}
          changeLabel="Cambiar documento"
          home={HOME_PATH.customer}
          requestCode={() => requestCode(sent.documentNumber)}
          openSession={(code) => openSession(sent.documentNumber, code)}
          onResent={(next) => setSent({ ...sent, ...next })}
          onChangeIdentity={() => setSent(null)}
        />
      ) : (
        <IdentityForm
          ready={trimmed !== ""}
          requestCode={() => requestCode(trimmed)}
          onSent={(expiresInSeconds) => setSent({ documentNumber: trimmed, expiresInSeconds, resent: false })}
        >
          <div>
            <label className="field-label" htmlFor={fieldId}>
              Número de documento
            </label>
            <input
              id={fieldId}
              className="field"
              autoComplete="off"
              spellCheck={false}
              value={documentNumber}
              onChange={(event) => setDocumentNumber(event.target.value)}
            />
          </div>
        </IdentityForm>
      )}
    </LoginShell>
  );
}
