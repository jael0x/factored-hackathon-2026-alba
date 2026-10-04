import { useState } from "react";

import { api } from "../api/client";
import type { components } from "../api/schema";
import { CodeStep, type CodeSent } from "../components/CodeStep";
import type { DemoSource } from "../components/DemoSearch";
import { DemoSearchPopover } from "../components/DemoSearchPopover";
import { IdentityForm } from "../components/IdentityForm";
import { LoginShell } from "../components/LoginShell";
import { TextField } from "../components/TextField";
import { fullName } from "../format";
import type { Messages } from "../i18n/es";
import { useLocale, type Locale } from "../i18n/locale";
import { useMessages } from "../i18n/messages";
import { HOME_PATH } from "../routes";
import { codeExpiry, sessionAnswer } from "../session/login";

type ConsultantHit = components["schemas"]["ConsultantSearchHit"];

type ConsultantIdentity = { email: string; employeeCode: string };

type Sent = CodeSent & ConsultantIdentity;

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
  const [sent, setSent] = useState<Sent | null>(null);
  const locale = useLocale();
  const t = useMessages();
  const copy = t.login.consultant;
  const typed: ConsultantIdentity = { email: email.trim(), employeeCode: employeeCode.trim() };

  const pick = (hit: ConsultantHit) => {
    setEmail(hit.email);
    setEmployeeCode(hit.employee_code);
    setSent(null);
  };

  return (
    <LoginShell
      role="consultant"
      title={copy.title}
      lede={copy.lede}
      notice={copy.notice}
      panelTitle={sent ? t.login.yourCode : copy.panelTitle}
      demo={
        <DemoSearchPopover
          source={consultantDemo(t.demo.consultants)}
          isSelected={(hit) => hit.email === email && hit.employee_code === employeeCode}
          onPick={pick}
        />
      }
    >
      {sent ? (
        <CodeStep
          identity={[
            { label: copy.email, value: sent.email },
            { label: copy.employeeCode, value: sent.employeeCode },
          ]}
          sent={sent}
          changeLabel={copy.change}
          home={HOME_PATH.consultant}
          requestCode={() => requestCode(sent, locale)}
          openSession={(code) => openSession(sent, code)}
          onResent={(next) => setSent({ ...sent, ...next })}
          onChangeIdentity={() => setSent(null)}
        />
      ) : (
        <IdentityForm
          ready={typed.email !== "" && typed.employeeCode !== ""}
          requestCode={() => requestCode(typed, locale)}
          onSent={(expiresInSeconds) => setSent({ ...typed, expiresInSeconds, resent: false })}
        >
          <TextField label={copy.email} type="email" autoComplete="email" value={email} onChange={setEmail} />
          <TextField
            label={copy.employeeCode}
            autoComplete="off"
            autoCapitalize="characters"
            value={employeeCode}
            onChange={setEmployeeCode}
          />
        </IdentityForm>
      )}
    </LoginShell>
  );
}
