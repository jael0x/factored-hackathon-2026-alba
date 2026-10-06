import { useMessages } from "../i18n/messages";
import type { DetailPart } from "../trace";

export function TracePart({ part }: { part: DetailPart }) {
  const t = useMessages();
  switch (part.kind) {
    case "quote":
      return <q className="trace-quote">{part.text}</q>;
    case "identifier":
      return <span className="mono">{part.text}</span>;
    case "tag":
      return <span className={`state-tag mono ${part.tone}`}>{part.text}</span>;
    case "word":
      return <span className="muted">{t.trace.words[part.word]}</span>;
    case "separator":
      return (
        <span className="muted" aria-hidden="true">
          ·
        </span>
      );
  }
}

export function TraceDetail({ parts }: { parts: readonly DetailPart[] }) {
  return (
    <p className="trace-detail">
      {parts.map((part, index) => (
        <TracePart key={index} part={part} />
      ))}
    </p>
  );
}
