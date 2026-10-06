import { useEffect, useMemo, useRef } from "react";
import { Link, Navigate, useParams } from "react-router";

import type { components } from "../api/schema";
import type { Loaded } from "../api/useLoad";
import { ErrorCard } from "../components/ErrorCard";
import { TraceEventCard } from "../components/TraceEventCard";
import { linksGutter, TraceLinks } from "../components/TraceLinks";
import { useMessages } from "../i18n/messages";
import { consultantCasePath, HOME_PATH } from "../routes";
import { causeOf, traceLinks } from "../trace";
import { useTrace, type TraceLoad } from "./useTrace";

type CaseTrace = components["schemas"]["CaseTrace"];

const PLACEHOLDER_CARDS = 4;

export function Trace() {
  const { processId } = useParams();
  if (processId === undefined) {
    return <Navigate to={HOME_PATH.consultant} replace />;
  }
  return <CaseTraceScreen key={processId} processId={processId} />;
}

function CaseTraceScreen({ processId }: { processId: string }) {
  const t = useMessages();
  const { trace, reload } = useTrace(processId);
  return (
    <>
      <nav className="crumbs" aria-label={t.consultant.crumbs}>
        <Link className="btn text" to={HOME_PATH.consultant}>
          {t.consultant.queue}
        </Link>
        <Chevron />
        <Link className="btn text" to={consultantCasePath(processId)}>
          {t.trace.caseCrumb}
        </Link>
        <Chevron />
        <span aria-current="page">{t.trace.crumb}</span>
      </nav>
      <TraceState trace={trace} onRetry={reload} />
    </>
  );
}

export function TraceState({ trace, onRetry }: { trace: Loaded<TraceLoad>; onRetry: () => void }) {
  const t = useMessages();
  if (trace.status === "loading") {
    return (
      <div className="trace-slots" role="status">
        <span className="sr-only">{t.loading}</span>
        {Array.from({ length: PLACEHOLDER_CARDS }, (_, index) => (
          <span key={index} className="pulse trace-slot" />
        ))}
      </div>
    );
  }
  if (trace.status === "error") {
    return <ErrorCard message={t.trace.loadFailed} onRetry={onRetry} />;
  }
  if (trace.data.kind === "unknown") {
    return (
      <section className="center-card solid enter" role="status">
        <h2 className="heading">{t.trace.unknown}</h2>
        <Link className="btn secondary" to={HOME_PATH.consultant}>
          {t.consultant.toQueue}
        </Link>
      </section>
    );
  }
  return <TraceView trace={trace.data.trace} />;
}

function Chevron() {
  return (
    <svg className="i" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M9 6l6 6-6 6" />
    </svg>
  );
}

// The order is the API's (events.seq); the screen numbers the events and never sorts them again.
// The connectors come after the list, so its anchors are attached when they measure.
export function TraceView({ trace }: { trace: CaseTrace }) {
  const t = useMessages();
  const list = useRef<HTMLOListElement>(null);
  const anchors = useRef<(HTMLElement | null)[]>([]);
  const { links, unresolved } = useMemo(() => traceLinks(trace.events), [trace]);
  const causes = useMemo(() => causeOf(links), [links]);
  const count = trace.events.length;

  useEffect(() => {
    unresolved.forEach(({ eventId, causeId }) =>
      console.error(`trace of ${trace.process_id}: event ${eventId} names cause ${causeId}, which is not in it`),
    );
  }, [trace.process_id, unresolved]);

  return (
    <>
      <div className="main-head">
        <div>
          <h1 className="title">{t.trace.title}</h1>
          <p className="caption muted">{t.trace.count(count)}</p>
          <p className="caption muted mono">{trace.process_id}</p>
        </div>
      </div>
      <div className="trace">
        <ol className="trace-events" ref={list} aria-label={t.trace.events} style={{ paddingLeft: linksGutter(links) }}>
          {trace.events.map((event, index) => {
            const cause = causes.get(index);
            return (
              <TraceEventCard
                key={event.id}
                event={event}
                number={index + 1}
                causeNumber={cause === undefined ? null : cause + 1}
                anchorRef={(anchor) => {
                  anchors.current[index] = anchor;
                }}
              />
            );
          })}
        </ol>
        <TraceLinks links={links} list={list} anchors={anchors} count={count} />
      </div>
    </>
  );
}
