import { useId, useState, type FormEvent } from "react";
import { useNavigate } from "react-router";

import { useMessages } from "../i18n/messages";
import type { SessionAnswer } from "../session/login";
import { startSession } from "../session/session";

export type CodeSent = { expiresInSeconds: number; resent: boolean };

type CodeStepProps = {
  identity: { label: string; value: string }[];
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
  sent,
  changeLabel,
  home,
  requestCode,
  openSession,
  onResent,
  onChangeIdentity,
}: CodeStepProps) {
  const fieldId = useId();
  const navigate = useNavigate();
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<CodeFailure>("none");
  const t = useMessages();
  const minutes = Math.round(sent.expiresInSeconds / 60);

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
            onChange={(event) => setCode(event.target.value.replace(/\D/g, ""))}
          />
          <p className="caption muted field-note">{t.code.validFor(minutes)}</p>
        </div>
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
