import { Link } from "react-router";

import type { components } from "../api/schema";
import { HUMAN_ACTIVE } from "../chat";
import { ErrorCard } from "../components/ErrorCard";
import { fullName } from "../format";
import { useMessages } from "../i18n/messages";
import { consultantCasePath } from "../routes";
import { STATE_TONE } from "../tones";
import { CaseCount, useConsultantShell } from "./ConsultantLayout";

type QueueItem = components["schemas"]["ConsultantQueueItem"];

const PLACEHOLDER_ROWS = 3;

export function ConsultantQueue() {
  const t = useMessages();
  const { queue, reloadQueue } = useConsultantShell();
  return (
    <>
      <div className="main-head">
        <h1 className="title">
          {t.consultant.queue} {queue.status === "ready" && <CaseCount count={queue.data.length} />}
        </h1>
      </div>
      {queue.status === "loading" && (
        <div role="status" className="queue-slots">
          <span className="sr-only">{t.loading}</span>
          {Array.from({ length: PLACEHOLDER_ROWS }, (_, index) => (
            <span key={index} className="pulse queue-slot" />
          ))}
        </div>
      )}
      {queue.status === "error" && <ErrorCard message={t.consultant.queueFailed} onRetry={reloadQueue} />}
      {queue.status === "ready" &&
        (queue.data.length === 0 ? (
          <p className="empty-queue solid enter">{t.consultant.queueEmpty}</p>
        ) : (
          <QueueTable items={queue.data} />
        ))}
    </>
  );
}

function QueueTable({ items }: { items: QueueItem[] }) {
  const t = useMessages();
  return (
    <div className="queue solid enter">
      <div className="queue-head caption muted" aria-hidden="true">
        <span>{t.consultant.columns.customer}</span>
        <span>{t.consultant.columns.product}</span>
        <span>{t.consultant.columns.reason}</span>
        <span>{t.consultant.columns.status}</span>
      </div>
      <ul className="queue-rows">
        {items.map((item) => (
          <li key={item.process_id}>
            <Link className="queue-row" to={consultantCasePath(item.process_id)}>
              <span className="label">{fullName(item)}</span>
              <span>{item.product && t.products.askAbout[item.product]}</span>
              <span className="mono caption">{item.reason_code}</span>
              <span>
                <span className={`state-tag ${STATE_TONE[HUMAN_ACTIVE]}`}>{t.consultant.inReview}</span>
              </span>
              <svg className="i" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M9 6l6 6-6 6" />
              </svg>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
