import type { Ref } from "react";

import type { components } from "../api/schema";
import { formatDateTime } from "../format";
import { useLocale } from "../i18n/locale";
import { useMessages } from "../i18n/messages";
import { analysisOf, traceDetail } from "../trace";
import { AnalysisRecord } from "./AnalysisRecord";
import { TraceDetail } from "./TraceDetail";

type TraceEvent = components["schemas"]["TraceEvent"];

type TraceEventCardProps = {
  event: TraceEvent;
  number: number;
  causeNumber: number | null;
  anchorRef: Ref<HTMLSpanElement>;
};

export function TraceEventCard({ event, number, causeNumber, anchorRef }: TraceEventCardProps) {
  const t = useMessages();
  const locale = useLocale();
  const analysis = analysisOf(event);
  return (
    <li className="trace-event solid enter">
      <span className="trace-marker glass" ref={anchorRef}>
        {number}
      </span>
      <div className="trace-body">
        <div className="trace-head">
          <span className="mono trace-name">{event.event_name}</span>
          <time className="caption muted" dateTime={event.created_at}>
            {formatDateTime(event.created_at, locale)}
          </time>
        </div>
        <TraceDetail parts={traceDetail(event)} />
        {causeNumber !== null && <p className="caption muted trace-cause">{t.trace.causedBy(causeNumber)}</p>}
        {analysis !== null && <AnalysisRecord analysis={analysis} />}
      </div>
    </li>
  );
}
