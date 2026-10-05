import { useEffect, useId, useState, type FormEvent } from "react";
import { useNavigate } from "react-router";

import { api } from "../api/client";
import { useLoad } from "../api/useLoad";
import { useMessages } from "../i18n/messages";
import { readDemoCode, type DemoMailbox } from "../session/demoCode";
import type { SessionAnswer } from "../session/login";
import { startSession } from "../session/session";

const loadConfig = () => api.GET("/config");

// The mail catcher and the browser share one clock in the local stack; the slack covers rounding only.
const DEMO_CLOCK_SLACK_MS = 2000;

export type CodeSent = { expiresInSeconds: number; resent: boolean };

type CodeStepProps = {
  identity: { label: string; value: string }[];
  demoMailbox: DemoMailbox;
  sent: CodeSent;
  changeLabel: string;
  home: string;
  requestCode: () => Promise<number | null>;
  openSession: (code: string) => Promise<SessionAnswer>;
  onResent: (sent: CodeSent) => void;
  onChangeIdentity: () => void;
};

type CodeFailure = "none" | "rejected" | "unreachable" | "resendFailed";

const CODE_PATTERN = /^[0-9]{6}$/;

export function CodeStep({
  identity,
  demoMailbox,
  sent,
  changeLabel,
  home,
  requestCode,
  openSession,
  onResent,
  onChangeIdentity,
}: CodeStepProps) {
  const [code, setCode] = useState("");
  const t = useMessages();
  const demoFilled = useDemoCode(demoMailbox, sent, setCode);
  const { busy, failure, submit, resend } = useCodeActions(code, setCode, home, openSession, requestCode, onResent);
  const minutes = Math.round(sent.expiresInSeconds / 60);

  return (
    <div className="stack">
      {identity.map((row) => (
        <div className="kv" key={row.label}>
          <span className="muted">{row.label}</span>
          <span>{row.value}</span>
        </div>
      ))}
      <p className="caption muted" role="status">
        {sent.resent ? t.code.resent : t.code.checkEmail}
      </p>
      <form className="stack" onSubmit={submit} noValidate>
        <CodeField code={code} onChange={setCode} minutes={minutes} demoFilled={demoFilled} />
        {failure !== "none" && (
          <p className="error-line" role="alert">
            {t.code[failure]}
          </p>
        )}
        <button type="submit" className="btn primary block" disabled={busy || !CODE_PATTERN.test(code)}>
          {t.code.open}
        </button>
      </form>
      <button type="button" className="btn secondary block" onClick={resend} disabled={busy}>
        {t.code.resend}
      </button>
      <button type="button" className="btn text centered" onClick={onChangeIdentity} disabled={busy}>
        {changeLabel}
      </button>
    </div>
  );
}

type CodeFieldProps = { code: string; onChange: (code: string) => void; minutes: number; demoFilled: boolean };

function CodeField({ code, onChange, minutes, demoFilled }: CodeFieldProps) {
  const fieldId = useId();
  const t = useMessages();
  return (
    <div>
      <label className="field-label" htmlFor={fieldId}>
        {t.code.label}
      </label>
      <input
        id={fieldId}
        className="field code"
        inputMode="numeric"
        autoFocus
        autoComplete="one-time-code"
        maxLength={6}
        value={code}
        onChange={(event) => onChange(event.target.value.replace(/\D/g, ""))}
      />
      <p className="caption muted field-note">{t.code.validFor(minutes)}</p>
      {demoFilled && <p className="caption muted field-note">{t.code.demoFilled}</p>}
    </div>
  );
}

// With DEMO_LOGIN on, the code is read back from the local mail catcher and filled in (PLAN.md D25).
function useDemoCode(mailbox: DemoMailbox, sent: CodeSent, fill: (code: string) => void): boolean {
  const [filled, setFilled] = useState(false);
  const config = useLoad(loadConfig);
  const demo = config.status === "ready" && config.data.demo_login;
  // The page builds a new mailbox object on every render; only its key says whether to read again.
  const mailboxKey = mailbox.kind === "sentTo" ? mailbox.address : mailbox.kind;

  useEffect(() => {
    if (!demo) {
      return;
    }
    let cancelled = false;
    void readDemoCode(Date.now() - DEMO_CLOCK_SLACK_MS, mailbox).then((found) => {
      if (!cancelled && found !== null) {
        fill(found);
        setFilled(true);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [demo, sent, mailboxKey]);

  return filled;
}

function useCodeActions(
  code: string,
  setCode: (code: string) => void,
  home: string,
  openSession: (code: string) => Promise<SessionAnswer>,
  requestCode: () => Promise<number | null>,
  onResent: (sent: CodeSent) => void,
) {
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<CodeFailure>("none");

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setFailure("none");
    const answer = await openSession(code);
    setBusy(false);
    if (answer.status === "opened") {
      startSession(answer.session);
      navigate(home, { replace: true });
      return;
    }
    setFailure(answer.status);
  };

  const resend = async () => {
    setBusy(true);
    setFailure("none");
    const expiresInSeconds = await requestCode();
    setBusy(false);
    if (expiresInSeconds === null) {
      setFailure("resendFailed");
      return;
    }
    setCode("");
    onResent({ expiresInSeconds, resent: true });
  };

  return { busy, failure, submit, resend };
}
