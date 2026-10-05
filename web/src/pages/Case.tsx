import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
  type ReactNode,
} from "react";
import { Link, Navigate, useLocation, useNavigate, useParams } from "react-router";

import { api } from "../api/client";
import type { components } from "../api/schema";
import { useLoad } from "../api/useLoad";
import { AppBar } from "../components/AppBar";
import { Certificate } from "../components/Certificate";
import { ErrorCard } from "../components/ErrorCard";
import { bubbleOf, newSend, showsTyping, type PendingSend } from "../chat";
import { isLocale, useLocale } from "../i18n/locale";
import { useMessages } from "../i18n/messages";
import { HOME_PATH, LOGIN_PATH, casePath } from "../routes";
import { signOut } from "../session/session";

type CaseData = components["schemas"]["Case"];

// What the home hands over when a product row opens the chat, or what a send hands to the case's own URL.
type Arrival = { opening?: PendingSend; case?: CaseData };

const loadMe = () => api.GET("/me");

function arrivalOf(state: unknown): Arrival {
  if (typeof state !== "object" || state === null) {
    return {};
  }
  const opening = "opening" in state && isPendingSend(state.opening) ? state.opening : undefined;
  const arrived = "case" in state && isCase(state.case) ? state.case : undefined;
  return { opening, case: arrived };
}

function isPendingSend(value: unknown): value is PendingSend {
  return (
    typeof value === "object" &&
    value !== null &&
    "text" in value &&
    typeof value.text === "string" &&
    "clientMessageId" in value &&
    typeof value.clientMessageId === "string" &&
    "locale" in value &&
    isLocale(value.locale)
  );
}

function isCase(value: unknown): value is CaseData {
  return (
    typeof value === "object" &&
    value !== null &&
    "process_id" in value &&
    typeof value.process_id === "string" &&
    "messages" in value &&
    Array.isArray(value.messages)
  );
}

type Answer = { case: CaseData } | { refused: number | null };

// A start names its product; any other message names its case (D24).
async function postMessage(message: PendingSend, processId: string | undefined): Promise<Answer> {
  const sent = { text: message.text, client_message_id: message.clientMessageId, locale: message.locale };
  const body = message.product ? { ...sent, product: message.product } : { ...sent, process_id: processId };
  const result = await api.POST("/messages", { body }).catch(() => null);
  if (result?.data) {
    return { case: result.data };
  }
  return { refused: result?.response.status ?? null };
}

const CONFLICT = 409;

export function Case() {
  const { processId } = useParams();
  const arrival = arrivalOf(useLocation().state);
  const navigate = useNavigate();
  const t = useMessages();
  const locale = useLocale();
  const me = useLoad(loadMe);
  const [caseData, setCaseData] = useState<CaseData | null>(arrival.case ?? null);
  const [loadFailed, setLoadFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [pending, setPending] = useState<PendingSend | null>(null);
  const [sendFailed, setSendFailed] = useState(false);
  const [appealing, setAppealing] = useState(false);
  const [appealFailed, setAppealFailed] = useState(false);
  const opened = useRef(false);

  const send = useCallback(
    async (message: PendingSend): Promise<boolean> => {
      setPending(message);
      setSendFailed(false);
      const answer = await postMessage(message, processId);
      if ("refused" in answer) {
        // The product already has a case, or this one has ended: the home or a fresh read shows which.
        if (answer.refused === CONFLICT) {
          setPending(null);
          if (message.product) {
            navigate(HOME_PATH.customer, { replace: true });
          } else {
            setAttempt((n) => n + 1);
          }
          return false;
        }
        setSendFailed(true);
        return false;
      }
      setPending(null);
      setCaseData(answer.case);
      if (answer.case.process_id !== processId) {
        navigate(casePath(answer.case.process_id), { replace: true, state: { case: answer.case } });
      }
      return true;
    },
    [navigate, processId],
  );

  useEffect(() => {
    if (processId === undefined && arrival.opening && !opened.current) {
      opened.current = true;
      void send(arrival.opening);
    }
  }, [processId, arrival.opening, send]);

  useEffect(() => {
    if (processId === undefined || (caseData?.process_id === processId && attempt === 0)) {
      return;
    }
    let cancelled = false;
    setLoadFailed(false);
    api
      .GET("/case/{process_id}", { params: { path: { process_id: processId } } })
      .then(({ data }) => {
        if (!cancelled) {
          if (data) {
            setCaseData(data);
          } else {
            setLoadFailed(true);
          }
        }
      })
      .catch(() => !cancelled && setLoadFailed(true));
    return () => {
      cancelled = true;
    };
  }, [processId, caseData?.process_id, attempt]);

  if (processId === undefined && !arrival.opening) {
    return <Navigate to={HOME_PATH.customer} replace />;
  }

  const leave = () => {
    signOut();
    navigate(LOGIN_PATH.customer, { replace: true });
  };
  const firstName = me.status === "ready" ? me.data.first_name : undefined;
  const state = caseData?.state ?? null;
  const ended = state === "ended";
  const certificate = caseData?.certificate ?? null;
  // A no the policy decided can be sent to a person once; the case then reopens (PLAN.md D25).
  const appealable = ended && certificate?.outcome === "NOT_PREQUALIFIED" && certificate.decided_by === "policy";

  const appeal = async () => {
    if (caseData === null) {
      return;
    }
    setAppealing(true);
    setAppealFailed(false);
    const { data } = await api
      .POST("/case/{process_id}/appeal", { params: { path: { process_id: caseData.process_id } }, body: { locale } })
      .catch(() => ({ data: undefined }));
    setAppealing(false);
    if (data) {
      setCaseData(data);
    } else {
      setAppealFailed(true);
    }
  };

  return (
    <>
      <AppBar firstName={firstName} onSignOut={leave} />
      <main className="chat">
        <Link className="btn text back" to={HOME_PATH.customer}>
          <svg className="i" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M15 6l-6 6 6 6" />
          </svg>
          {t.chat.back}
        </Link>
        {loadFailed ? (
          <ErrorCard message={t.chat.loadFailed} onRetry={() => setAttempt((n) => n + 1)} />
        ) : (
          <Thread
            caseData={caseData}
            pending={pending}
            typing={showsTyping(pending !== null && !sendFailed, state)}
            firstName={firstName}
            certificate={
              caseData?.certificate && (
                <Certificate
                  certificate={caseData.certificate}
                  appeal={appealable ? { busy: appealing, failed: appealFailed, onAppeal: () => void appeal() } : null}
                />
              )
            }
          />
        )}
      </main>
      <div className="dock">
        {state === "human_active" && <p className="banner solid">{t.chat.withPerson}</p>}
        {sendFailed && pending && (
          <div className="actions-row send-failed" role="alert">
            <p className="error-line">{t.chat.sendFailed}</p>
            <button type="button" className="btn text" onClick={() => void send(pending)}>
              {t.retry}
            </button>
          </div>
        )}
        {ended ? (
          <Link className="btn secondary back-home" to={HOME_PATH.customer}>
            {t.chat.backHome}
          </Link>
        ) : (
          <Composer sending={pending !== null && !sendFailed} onSend={(text) => send(newSend(text, locale))} />
        )}
      </div>
    </>
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
          const bubble = bubbleOf(line.author);
          return (
            <li key={line.id} className={`msg ${bubble.side} enter`}>
              <Author side={bubble.side} firstName={firstName} />
              <div className={`bubble ${bubble.surface === "solid" ? "solid" : "glass"} ${bubble.surface}`}>
                {line.body}
              </div>
            </li>
          );
        })}
        {certificate && !lines.some((line) => line.event_id === caseData?.certificate?.event_id) && (
          <li className="msg-certificate">{certificate}</li>
        )}
        {pending && (
          <li className="msg me enter">
            <Author side="me" firstName={firstName} />
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

function Author({ side, firstName }: { side: "me" | "alba"; firstName: string | undefined }) {
  const t = useMessages();
  if (side === "me") {
    return <span className="who caption muted">{firstName}</span>;
  }
  return (
    <span className="who caption muted">
      <span className="orb small" aria-hidden="true" />
      {t.chat.assistant}
    </span>
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
