import { useState, type FormEvent, type ReactNode } from "react";

import { useMessages } from "../i18n/messages";

type IdentityFormProps = {
  ready: boolean;
  requestCode: () => Promise<number | null>;
  onSent: (expiresInSeconds: number) => void;
  children: ReactNode;
};

export function IdentityForm({ ready, requestCode, onSent, children }: IdentityFormProps) {
  const [sending, setSending] = useState(false);
  const [failed, setFailed] = useState(false);
  const t = useMessages();

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSending(true);
    setFailed(false);
    const expiresInSeconds = await requestCode();
    setSending(false);
    if (expiresInSeconds === null) {
      setFailed(true);
      return;
    }
    onSent(expiresInSeconds);
  };

  return (
    <form className="stack" onSubmit={submit} noValidate>
      {children}
      {failed && (
        <p className="error-line" role="alert">
          {t.login.sendFailed}
        </p>
      )}
      <button type="submit" className="btn primary block" disabled={sending || !ready}>
        {sending ? t.login.sending : t.login.sendCode}
      </button>
    </form>
  );
}
