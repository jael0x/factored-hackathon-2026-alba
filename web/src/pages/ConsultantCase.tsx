import { useCallback, useEffect, useState } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router";

import type { components } from "../api/schema";
import { useLoad } from "../api/useLoad";
import { CloseDialog } from "../components/CloseDialog";
import { ErrorCard } from "../components/ErrorCard";
import { HandoffPacket } from "../components/HandoffPacket";
import { MessageLine } from "../components/MessageLine";
import { closeActions, type CloseAnswer } from "../consultant";
import { fullName } from "../format";
import { useMessages } from "../i18n/messages";
import { HOME_PATH } from "../routes";
import { useConsultantShell } from "./ConsultantLayout";
import { loadConsultantCase, useClose } from "./useClose";

type ConsultantCaseData = components["schemas"]["ConsultantCase"];
type CloseOutcome = components["schemas"]["CloseOutcome"];

export function ConsultantCase() {
  const { processId } = useParams();
  if (processId === undefined) {
    return <Navigate to={HOME_PATH.consultant} replace />;
  }
  return <OpenCase key={processId} processId={processId} />;
}

function OpenCase({ processId }: { processId: string }) {
  const t = useMessages();
  const navigate = useNavigate();
  const { reloadQueue } = useConsultantShell();
  const [attempt, setAttempt] = useState(0);
  const reload = useCallback(() => setAttempt((n) => n + 1), []);
  const load = useCallback(() => loadConsultantCase(processId), [processId]);
  const found = useLoad(load, attempt);

  const closed = useCallback(() => {
    reloadQueue();
    navigate(HOME_PATH.consultant);
  }, [reloadQueue, navigate]);
  const { closing, answer, close } = useClose(processId, closed, reload);

  const gone = found.status === "ready" && found.data.kind === "gone";
  useEffect(() => {
    if (gone) {
      reloadQueue();
    }
  }, [gone, reloadQueue]);

  if (found.status === "loading") {
    return (
      <p role="status" className="pulse case-slot">
        <span className="sr-only">{t.loading}</span>
      </p>
    );
  }
  if (found.status === "error") {
    return <ErrorCard message={t.consultant.caseFailed} onRetry={reload} />;
  }
  if (found.data.kind === "gone") {
    return (
      <section className="center-card solid enter" role="status">
        <h2 className="heading">{t.consultant.gone}</h2>
        <Link className="btn secondary" to={HOME_PATH.consultant}>
          {t.consultant.toQueue}
        </Link>
      </section>
    );
  }
  return (
    <ConsultantCaseView
      packet={found.data.packet}
      answer={answer}
      closing={closing}
      onClose={close}
      onRefresh={reload}
    />
  );
}

type ConsultantCaseViewProps = {
  packet: ConsultantCaseData;
  answer: CloseAnswer | null;
  closing: boolean;
  onClose: (outcome: CloseOutcome) => Promise<void>;
  onRefresh: () => void;
};

// The thread is read only: the consultant's one action is a close the packet allows (ARCHITECTURE.md "Consultant close").
export function ConsultantCaseView({ packet, answer, closing, onClose, onRefresh }: ConsultantCaseViewProps) {
  const t = useMessages();
  const [choice, setChoice] = useState<CloseOutcome | null>(null);
  const name = fullName(packet);

  const confirm = async (outcome: CloseOutcome) => {
    await onClose(outcome);
    setChoice(null);
  };

  return (
    <>
      <nav className="crumbs" aria-label={t.consultant.crumbs}>
        <Link className="btn text" to={HOME_PATH.consultant}>
          {t.consultant.queue}
        </Link>
        <svg className="i" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M9 6l6 6-6 6" />
        </svg>
        <span aria-current="page">{name}</span>
      </nav>
      <div className="main-head">
        <div>
          <h1 className="title">{name}</h1>
          <p className="caption muted mono">{packet.customer_id}</p>
        </div>
        <span className="state-tag clay">{t.consultant.inReview}</span>
      </div>
      {answer !== null && answer.kind !== "closed" && <CloseNotice answer={answer} onRefresh={onRefresh} />}
      <div className="split">
        <section className="convo glass" aria-label={t.consultant.conversation}>
          <h2 className="heading">{t.consultant.conversation}</h2>
          <ol className="thread" lang={packet.locale}>
            {packet.messages.map((line) => (
              <MessageLine key={line.id} line={line} customerName={packet.first_name} />
            ))}
          </ol>
        </section>
        <HandoffPacket packet={packet} actions={closeActions(packet, answer)} onChoose={setChoice} />
      </div>
      <CloseDialog
        outcome={choice}
        customerName={packet.first_name}
        closing={closing}
        onConfirm={(outcome) => void confirm(outcome)}
        onCancel={() => setChoice(null)}
      />
    </>
  );
}

function CloseNotice({ answer, onRefresh }: { answer: Exclude<CloseAnswer, { kind: "closed" }>; onRefresh: () => void }) {
  const t = useMessages();
  if (answer.kind === "pending") {
    return (
      <div className="actions-row close-notice" role="status">
        <p className="error-line">{t.consultant.answers.pending}</p>
        <button type="button" className="btn text" onClick={onRefresh}>
          {t.consultant.refresh}
        </button>
      </div>
    );
  }
  const message =
    answer.kind === "not_closable"
      ? t.consultant.notClosable
      : answer.kind === "gone"
        ? t.consultant.gone
        : t.consultant.answers[answer.kind];
  return (
    <p className="error-line close-notice" role="alert">
      {message}
    </p>
  );
}
