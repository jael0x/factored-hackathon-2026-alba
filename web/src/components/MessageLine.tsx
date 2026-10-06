import type { components } from "../api/schema";
import { bubbleOf } from "../chat";
import { useMessages } from "../i18n/messages";

type ThreadMessage = components["schemas"]["ThreadMessage"];

// DESIGN.md "Messages": one line of a thread, the same on the customer's case and the consultant's.
export function MessageLine({ line, customerName }: { line: ThreadMessage; customerName: string | undefined }) {
  const bubble = bubbleOf(line.author);
  return (
    <li className={`msg ${bubble.side} enter`}>
      <Author side={bubble.side} customerName={customerName} />
      <div className={`bubble ${bubble.surface === "solid" ? "solid" : "glass"} ${bubble.surface}`}>{line.body}</div>
    </li>
  );
}

export function Author({ side, customerName }: { side: "me" | "alba"; customerName: string | undefined }) {
  const t = useMessages();
  if (side === "me") {
    return <span className="who caption muted">{customerName}</span>;
  }
  return (
    <span className="who caption muted">
      <span className="orb small" aria-hidden="true" />
      {t.chat.assistant}
    </span>
  );
}
