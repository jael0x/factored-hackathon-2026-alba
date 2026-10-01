import { useId, useState } from "react";

import { api } from "../api/client";
import type { components } from "../api/schema";
import { CodeStep, type CodeSent } from "../components/CodeStep";
import type { DemoSource } from "../components/DemoSearch";
import { DemoSearchPopover } from "../components/DemoSearchPopover";
import { IdentityForm } from "../components/IdentityForm";
import { LoginShell } from "../components/LoginShell";
import { fullName } from "../format";
import { HOME_PATH } from "../routes";
import { codeExpiry, sessionAnswer } from "../session/login";

type AgentHit = components["schemas"]["AgentSearchHit"];

type AgentIdentity = { email: string; employeeCode: string };

type Sent = CodeSent & AgentIdentity;

const agentDemo: DemoSource<AgentHit> = {
  heading: "Agentes de prueba",
  help: "Solo en el demo. Elegir a alguien llena su correo y su código de empleado y cierra este panel; el código igual llega por correo.",
  queryLabel: "Nombre, código de empleado o número de agente",
  search: async (q) => {
    const { data } = await api.GET("/agents/search", { params: { query: { q } } }).catch(() => ({ data: undefined }));
    return data ? data.agents : null;
  },
  pickRandom: async () => {
    const { data } = await api
      .GET("/agents/search", { params: { query: { random: true } } })
      .catch(() => ({ data: undefined }));
    return data?.agents[0] ?? null;
  },
  key: (hit) => hit.agent_id,
  render: (hit) => (
    <>
      <span className="name">{fullName(hit)}</span>
      <br />
      <span className="caption muted">
        código de empleado <span className="mono">{hit.employee_code}</span>
      </span>
    </>
  ),
};

const requestCode = ({ email, employeeCode }: AgentIdentity) =>
  codeExpiry(api.POST("/agent/session/code", { body: { email, employee_code: employeeCode } }));

const openSession = ({ email, employeeCode }: AgentIdentity, code: string) =>
  sessionAnswer(api.POST("/agent/session", { body: { email, employee_code: employeeCode, code } }));

export function AgentLogin() {
  const emailId = useId();
  const employeeCodeId = useId();
  const [email, setEmail] = useState("");
  const [employeeCode, setEmployeeCode] = useState("");
  const [sent, setSent] = useState<Sent | null>(null);
  const typed: AgentIdentity = { email: email.trim(), employeeCode: employeeCode.trim() };

  const pick = (hit: AgentHit) => {
    setEmail(hit.email);
    setEmployeeCode(hit.employee_code);
    setSent(null);
  };

  return (
    <LoginShell
      role="agent"
      title="Entra como agente"
      lede="Escribe tu correo y tu código de empleado. Te enviaremos un código de un solo uso a ese correo."
      notice="Si tus datos corresponden a un agente activo, te enviaremos un código."
      panelTitle={sent ? "Tu código" : "Tus datos"}
      demo={
        <DemoSearchPopover
          source={agentDemo}
          isSelected={(hit) => hit.email === email && hit.employee_code === employeeCode}
          onPick={pick}
        />
      }
    >
      {sent ? (
        <CodeStep
          identity={[
            { label: "Correo", value: sent.email },
            { label: "Código de empleado", value: sent.employeeCode },
          ]}
          sent={sent}
          changeLabel="Cambiar datos"
          home={HOME_PATH.agent}
          requestCode={() => requestCode(sent)}
          openSession={(code) => openSession(sent, code)}
          onResent={(next) => setSent({ ...sent, ...next })}
          onChangeIdentity={() => setSent(null)}
        />
      ) : (
        <IdentityForm
          ready={typed.email !== "" && typed.employeeCode !== ""}
          requestCode={() => requestCode(typed)}
          onSent={(expiresInSeconds) => setSent({ ...typed, expiresInSeconds, resent: false })}
        >
          <div>
            <label className="field-label" htmlFor={emailId}>
              Correo
            </label>
            <input
              id={emailId}
              className="field"
              type="email"
              autoComplete="email"
              spellCheck={false}
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>
          <div>
            <label className="field-label" htmlFor={employeeCodeId}>
              Código de empleado
            </label>
            <input
              id={employeeCodeId}
              className="field"
              autoComplete="off"
              autoCapitalize="characters"
              spellCheck={false}
              value={employeeCode}
              onChange={(event) => setEmployeeCode(event.target.value)}
            />
          </div>
        </IdentityForm>
      )}
    </LoginShell>
  );
}
