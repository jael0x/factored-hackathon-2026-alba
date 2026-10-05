import { useState } from "react";

import { api } from "../api/client";
import type { components } from "../api/schema";
import type { DemoSource } from "../components/DemoSearch";
import { DemoSearchPopover } from "../components/DemoSearchPopover";
import { LoginShell } from "../components/LoginShell";
import { LoginSteps, type SentTo } from "../components/LoginSteps";
import { TextField } from "../components/TextField";
import { fullName } from "../format";
import type { Messages } from "../i18n/es";
import type { Locale } from "../i18n/locale";
import { useMessages } from "../i18n/messages";
import { codeExpiry, sessionAnswer } from "../session/login";

type ConsultantHit = components["schemas"]["ConsultantSearchHit"];

type ConsultantIdentity = { email: string; employeeCode: string };

const searchConsultants = async (q: string) => {
  const { data } = await api.GET("/consultants/search", { params: { query: { q } } }).catch(() => ({ data: undefined }));
  return data ? data.consultants : null;
};

const pickRandomConsultant = async () => {
  const { data } = await api
    .GET("/consultants/search", { params: { query: { random: true } } })
    .catch(() => ({ data: undefined }));
  return data?.consultants[0] ?? null;
};

const consultantDemo = (copy: Messages["demo"]["consultants"]): DemoSource<ConsultantHit> => ({
  heading: copy.heading,
  help: copy.help,
  queryLabel: copy.queryLabel,
  search: searchConsultants,
  pickRandom: pickRandomConsultant,
  key: (hit) => hit.consultant_id,
  render: (hit) => (
    <>
      <span className="name">{fullName(hit)}</span>
      <br />
      <span className="caption muted">
        {copy.employeeCode} <span className="mono">{hit.employee_code}</span>
      </span>
    </>
  ),
});

const requestCode = ({ email, employeeCode }: ConsultantIdentity, locale: Locale) =>
  codeExpiry(api.POST("/consultant/session/code", { body: { email, employee_code: employeeCode, locale } }));

const openSession = ({ email, employeeCode }: ConsultantIdentity, code: string) =>
  sessionAnswer(api.POST("/consultant/session", { body: { email, employee_code: employeeCode, code } }));

export function ConsultantLogin() {
  const [email, setEmail] = useState("");
  const [employeeCode, setEmployeeCode] = useState("");
  const [sent, setSent] = useState<SentTo<ConsultantIdentity> | null>(null);
  const t = useMessages();
  const copy = t.login.consultant;
  const typed = { email: email.trim(), employeeCode: employeeCode.trim() };

  const pick = (hit: ConsultantHit) => {
    setEmail(hit.email);
    setEmployeeCode(hit.employee_code);
    setSent(null);
  };

  return (
    <LoginShell
      role="consultant"
      codeSent={sent !== null}
      demo={
        <DemoSearchPopover
          source={consultantDemo(t.demo.consultants)}
          isSelected={(hit) => hit.email === email && hit.employee_code === employeeCode}
          onPick={pick}
        />
      }
    >
      <LoginSteps
        role="consultant"
        typed={typed.email === "" || typed.employeeCode === "" ? null : typed}
        sent={sent}
        onSentChange={setSent}
        identityRows={(identity) => [
          { label: copy.email, value: identity.email },
          { label: copy.employeeCode, value: identity.employeeCode },
        ]}
        demoMailbox={(identity) => ({ kind: "sentTo", address: identity.email })}
        requestCode={requestCode}
        openSession={openSession}
      >
        <TextField label={copy.email} type="email" autoComplete="email" value={email} onChange={setEmail} />
        <TextField label={copy.employeeCode} autoCapitalize="characters" value={employeeCode} onChange={setEmployeeCode} />
      </LoginSteps>
    </LoginShell>
  );
}
