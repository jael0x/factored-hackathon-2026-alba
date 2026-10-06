import { useEffect, useId, useRef, useState, type FormEvent, type KeyboardEvent, type ReactNode } from "react";
import { Link, Navigate, useLocation, useNavigate, useParams } from "react-router";

import { api } from "../api/client";
import { useLoad } from "../api/useLoad";
import { AppBar } from "../components/AppBar";
import { Certificate } from "../components/Certificate";
import { ErrorCard } from "../components/ErrorCard";
import { Author, MessageLine } from "../components/MessageLine";
import { ENDED, HUMAN_ACTIVE, newSend, showsTyping, type PendingSend } from "../chat";
import { useLocale } from "../i18n/locale";
import { useMessages } from "../i18n/messages";
import { HOME_PATH, LOGIN_PATH } from "../routes";
import { signOut } from "../session/session";
import { arrivalOf, useAppeal, useCase, useOpening, useSend, type CaseData } from "./useCase";

const loadMe = () => api.GET("/me");

export function Case() {
  const { processId } = useParams();
  const arrival = arrivalOf(useLocation().state);
  const navigate = useNavigate();
  const t = useMessages();
  const locale = useLocale();
  const me = useLoad(loadMe);
  const { caseData, setCaseData, loading, loadFailed, reload } = useCase(processId, arrival.case);
  const { pending, failed: sendFailed, send } = useSend(processId, setCaseData, reload);
  const appeal = useAppeal(caseData?.process_id, setCaseData);
  useOpening(processId, arrival.opening, send);

  if (processId === undefined && !arrival.opening) {
    return <Navigate to={HOME_PATH.customer} replace />;
  }

  const leave = () => {
    signOut();
    navigate(LOGIN_PATH.customer, { replace: true });
  };
  const firstName = me.status === "ready" ? me.data.first_name : undefined;
  const author = me.status === "error" ? t.chat.you : firstName;
  const state = caseData?.state ?? null;

  return (
    <>
      <AppBar firstName={firstName} onSignOut={leave} />
      <main className="chat">
        <BackLink />
        {loading && (
          <p role="status" className="pulse greeting">
            <span className="sr-only">{t.loading}</span>
          </p>
        )}
        {loadFailed ? (
          <ErrorCard message={t.chat.loadFailed} onRetry={reload} />
        ) : (
          !loading && (
            <Thread
              caseData={caseData}
              pending={pending}
              typing={showsTyping(pending !== null && !sendFailed, state)}
              firstName={author}
              certificate={certificateCard(caseData, appeal)}
            />
          )
        )}
      </main>
      <Dock
        state={state}
        retry={sendFailed ? pending : null}
        sending={pending !== null && !sendFailed}
        send={send}
        onSend={(text) => send(newSend(text, locale))}
      />
    </>
  );
}

function BackLink() {
  const t = useMessages();
  return (
    <Link className="btn text back" to={HOME_PATH.customer}>
      <svg className="i" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M15 6l-6 6 6 6" />
      </svg>
      {t.chat.back}
    </Link>
  );
}

function certificateCard(caseData: CaseData | null, appeal: ReturnType<typeof useAppeal>): ReactNode {
  if (!caseData?.certificate) {
    return null;
  }
  const offer = caseData.appealable
    ? {
        busy: appeal.busy,
        failed: appeal.failed,
        onAppeal: () => void appeal.appeal(),
      }
    : null;
  return <Certificate certificate={caseData.certificate} appeal={offer} />;
}

type DockProps = {
  state: CaseData["state"] | null;
  retry: PendingSend | null;
  sending: boolean;
  send: (message: PendingSend) => Promise<boolean>;
  onSend: (text: string) => Promise<boolean>;
};

function Dock({ state, retry, sending, send, onSend }: DockProps) {
  const t = useMessages();
  return (
    <div className="dock">
      {state === HUMAN_ACTIVE && <p className="banner solid">{t.chat.withPerson}</p>}
      {retry && (
        <div className="actions-row send-failed" role="alert">
          <p className="error-line">{t.chat.sendFailed}</p>
          <button type="button" className="btn text" onClick={() => void send(retry)}>
            {t.retry}
          </button>
        </div>
      )}
      {state === ENDED ? (
        <Link className="btn secondary back-home" to={HOME_PATH.customer}>
          {t.chat.backHome}
        </Link>
      ) : (
        <Composer sending={sending} onSend={onSend} />
      )}
    </div>
  );
}

type ThreadProps = {
  caseData: CaseData | null;
  pending: PendingSend | null;
  typing: boolean;
  firstName: string | undefined;
  certificate: ReactNode;
};

// The certificate takes the place of its own thread line, so a notice that follows it reads below it (D25).
// A case decided before that line existed shows it after the thread.
function Thread({ caseData, pending, typing, firstName, certificate }: ThreadProps) {
  const t = useMessages();
  const lines = caseData?.messages ?? [];
  const end = useRef<HTMLDivElement>(null);
  const shown = lines.length + (pending ? 1 : 0) + (typing ? 1 : 0);

  // The newest line stays in view above the composer, without motion when the reader asked for less.
  useEffect(() => {
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    end.current?.scrollIntoView({ block: "end", behavior: still ? "auto" : "smooth" });
  }, [shown]);

  return (
    <>
      <ol className="thread" aria-label={t.chat.thread} aria-live="polite" lang={caseData?.locale}>
        {lines.map((line) => {
          if (line.event_id === caseData?.certificate?.event_id) {
            return (
              <li key={line.id} className="msg-certificate">
                {certificate}
              </li>
            );
          }
          return <MessageLine key={line.id} line={line} customerName={firstName} />;
        })}
        {certificate && !lines.some((line) => line.event_id === caseData?.certificate?.event_id) && (
          <li className="msg-certificate">{certificate}</li>
        )}
        {pending && (
          <li className="msg me enter">
            <Author side="me" customerName={firstName} />
            <div className="bubble glass tinted">{pending.text}</div>
          </li>
        )}
        {typing && (
          <li className="msg alba">
            <span className="typing glass">
              <span className="orb small" aria-hidden="true" />
              <span className="caption muted">{t.chat.typing}</span>
            </span>
          </li>
        )}
      </ol>
      <div ref={end} className="thread-end" />
    </>
  );
}

function Composer({ sending, onSend }: { sending: boolean; onSend: (text: string) => Promise<boolean> }) {
  const t = useMessages();
  const fieldId = useId();
  const [draft, setDraft] = useState("");
  const text = draft.trim();

  const submit = async (event?: FormEvent) => {
    event?.preventDefault();
    if (text === "" || sending) {
      return;
    }
    if (await onSend(text)) {
      setDraft("");
    }
  };

  const sendOnEnter = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void submit();
    }
  };

  return (
    <form className="composer glass" onSubmit={(event) => void submit(event)}>
      <label className="sr-only" htmlFor={fieldId}>
        {t.chat.composer}
      </label>
      <textarea
        id={fieldId}
        rows={1}
        placeholder={t.chat.composer}
        value={draft}
        readOnly={sending}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={sendOnEnter}
      />
      <button type="submit" className="send" aria-label={t.chat.send} disabled={text === "" || sending}>
        {sending ? (
          <span className="spinner" aria-hidden="true" />
        ) : (
          <svg className="i" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 19V5M6 11l6-6 6 6" />
          </svg>
        )}
      </button>
    </form>
  );
}
