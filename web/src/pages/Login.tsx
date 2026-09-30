import { useEffect, useId, useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router";

import { api } from "../api/client";
import { AppBar } from "../components/AppBar";
import { DemoSearchPopover } from "../components/DemoSearchPopover";
import { startSession, useSession } from "../session/session";

type Step =
  | { kind: "document" }
  | { kind: "code"; documentNumber: string; expiresInSeconds: number; resent: boolean };

type DemoConfig = { status: "loading" } | { status: "error" } | { status: "ready"; demoLogin: boolean };

const CODE_PATTERN = /^[0-9]{6}$/;

export function Login() {
  const session = useSession();
  const demo = useDemoConfig();
  const [documentNumber, setDocumentNumber] = useState("");
  const [step, setStep] = useState<Step>({ kind: "document" });

  if (session.status === "active") {
    return <Navigate to="/" replace />;
  }

  const pickDocument = (value: string) => {
    setDocumentNumber(value);
    setStep({ kind: "document" });
  };

  const showDemo = demo.status === "ready" && demo.demoLogin;

  return (
    <>
      <AppBar tools={showDemo ? <DemoSearchPopover selectedDocument={documentNumber} onPick={pickDocument} /> : undefined} />
      <main className="page login-layout">
        <div className="intro">
          <h1 className="display">Entra a tu cuenta</h1>
          <p className="lede">Escribe tu número de documento. Te enviaremos un código de un solo uso al correo registrado.</p>
          <p className="notice">
            Si tu documento está registrado y tiene un correo asociado, te enviaremos un código. Si no te llega, acércate a
            una sucursal para registrar tu correo.
          </p>
          {demo.status === "error" && <p className="caption muted">No pudimos leer la configuración del demo.</p>}
        </div>
        <div className="login-form">
          <section className="panel glass" aria-labelledby="login-title">
            <div className="panel-head">
              <h2 className="heading" id="login-title">
                {step.kind === "document" ? "Tu documento" : "Tu código"}
              </h2>
            </div>
            {step.kind === "document" ? (
              <DocumentStep documentNumber={documentNumber} onChange={setDocumentNumber} onSent={setStep} />
            ) : (
              <CodeStep step={step} onResent={setStep} onChangeDocument={() => setStep({ kind: "document" })} />
            )}
          </section>
        </div>
      </main>
    </>
  );
}

function useDemoConfig(): DemoConfig {
  const [config, setConfig] = useState<DemoConfig>({ status: "loading" });
  useEffect(() => {
    let cancelled = false;
    api
      .GET("/config")
      .then(({ data }) => {
        if (!cancelled) {
          setConfig(data ? { status: "ready", demoLogin: data.demo_login } : { status: "error" });
        }
      })
      .catch(() => {
        if (!cancelled) {
          setConfig({ status: "error" });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);
  return config;
}

async function requestCode(documentNumber: string): Promise<number | null> {
  const { data } = await api
    .POST("/session/code", { body: { document_number: documentNumber } })
    .catch(() => ({ data: undefined }));
  return data ? data.expires_in_seconds : null;
}

type DocumentStepProps = {
  documentNumber: string;
  onChange: (value: string) => void;
  onSent: (step: Step) => void;
};

function DocumentStep({ documentNumber, onChange, onSent }: DocumentStepProps) {
  const fieldId = useId();
  const [sending, setSending] = useState(false);
  const [failed, setFailed] = useState(false);
  const trimmed = documentNumber.trim();

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSending(true);
    setFailed(false);
    const expiresInSeconds = await requestCode(trimmed);
    setSending(false);
    if (expiresInSeconds === null) {
      setFailed(true);
      return;
    }
    onSent({ kind: "code", documentNumber: trimmed, expiresInSeconds, resent: false });
  };

  return (
    <form className="stack" onSubmit={submit} noValidate>
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
          onChange={(event) => onChange(event.target.value)}
        />
      </div>
      {failed && (
        <p className="error-line" role="alert">
          No pudimos enviar la solicitud. Inténtalo de nuevo.
        </p>
      )}
      <button type="submit" className="btn primary block" disabled={sending || trimmed === ""}>
        {sending ? "Enviando…" : "Enviar código"}
      </button>
    </form>
  );
}

type CodeStepProps = {
  step: Extract<Step, { kind: "code" }>;
  onResent: (step: Step) => void;
  onChangeDocument: () => void;
};

type CodeFailure = "none" | "rejected" | "unreachable" | "resend_failed";

function CodeStep({ step, onResent, onChangeDocument }: CodeStepProps) {
  const fieldId = useId();
  const navigate = useNavigate();
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<CodeFailure>("none");
  const minutes = Math.round(step.expiresInSeconds / 60);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setFailure("none");
    const result = await api
      .POST("/session", { body: { document_number: step.documentNumber, code } })
      .catch(() => null);
    setBusy(false);
    if (result?.data) {
      startSession(result.data);
      navigate("/", { replace: true });
      return;
    }
    setFailure(result?.response.status === 401 ? "rejected" : "unreachable");
  };

  const resend = async () => {
    setBusy(true);
    setFailure("none");
    const expiresInSeconds = await requestCode(step.documentNumber);
    setBusy(false);
    if (expiresInSeconds === null) {
      setFailure("resend_failed");
      return;
    }
    setCode("");
    onResent({ ...step, expiresInSeconds, resent: true });
  };

  return (
    <div className="stack">
      <div className="kv">
        <span className="muted">Documento</span>
        <span>{step.documentNumber}</span>
      </div>
      <p className="caption muted" role="status">
        {step.resent ? "Pedimos otro código. Revisa tu correo." : "Revisa tu correo y escribe el código."}
      </p>
      <form className="stack" onSubmit={submit} noValidate>
        <div>
          <label className="field-label" htmlFor={fieldId}>
            Código
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
          <p className="caption muted field-note">El código vale {minutes} minutos.</p>
        </div>
        {failure !== "none" && (
          <p className="error-line" role="alert">
            {failureText[failure]}
          </p>
        )}
        <button type="submit" className="btn primary block" disabled={busy || !CODE_PATTERN.test(code)}>
          Abrir sesión
        </button>
      </form>
      <button type="button" className="btn secondary block" onClick={resend} disabled={busy}>
        Pedir otro código
      </button>
      <button type="button" className="btn text centered" onClick={onChangeDocument} disabled={busy}>
        Cambiar documento
      </button>
    </div>
  );
}

const failureText: Record<Exclude<CodeFailure, "none">, string> = {
  rejected: "El código no es válido o venció.",
  unreachable: "No pudimos abrir la sesión. Inténtalo de nuevo.",
  resend_failed: "No pudimos pedir otro código. Inténtalo de nuevo.",
};
