import { useState, type FormEvent, type ReactNode } from "react";

type IdentityFormProps = {
  ready: boolean;
  requestCode: () => Promise<number | null>;
  onSent: (expiresInSeconds: number) => void;
  children: ReactNode;
};

export function IdentityForm({ ready, requestCode, onSent, children }: IdentityFormProps) {
  const [sending, setSending] = useState(false);
  const [failed, setFailed] = useState(false);

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
          No pudimos enviar la solicitud. Inténtalo de nuevo.
        </p>
      )}
      <button type="submit" className="btn primary block" disabled={sending || !ready}>
        {sending ? "Enviando…" : "Enviar código"}
      </button>
    </form>
  );
}
