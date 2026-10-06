import { useId } from "react";

import type { components } from "../api/schema";
import { packetRows } from "../consultant";
import { useMessages } from "../i18n/messages";

type ConsultantCase = components["schemas"]["ConsultantCase"];
type CloseOutcome = components["schemas"]["CloseOutcome"];

type HandoffPacketProps = {
  packet: ConsultantCase;
  actions: readonly CloseOutcome[];
  onChoose: (outcome: CloseOutcome) => void;
};

export function HandoffPacket({ packet, actions, onChoose }: HandoffPacketProps) {
  const t = useMessages();
  const titleId = useId();
  const rows = packetRows(packet, (product) => t.products.askAbout[product]);
  return (
    <article className="packet" aria-labelledby={titleId}>
      <h2 className="kicker" id={titleId}>
        {t.consultant.packet}
      </h2>
      <dl className="facts">
        {rows.map((row) => (
          <div key={row.field}>
            <dt>{t.consultant.rows[row.field]}</dt>
            <dd className={row.identifier ? "mono" : undefined}>{row.value}</dd>
          </div>
        ))}
      </dl>
      {!packet.closable && <p className="packet-note">{t.consultant.notClosable}</p>}
      {actions.length > 0 && (
        <div className="packet-close">
          <h3 className="kicker">{t.consultant.closeTitle}</h3>
          <div className="packet-actions">
            {actions.map((outcome) => (
              <button key={outcome} type="button" className="btn hero-secondary" onClick={() => onChoose(outcome)}>
                {t.consultant.close[outcome]}
              </button>
            ))}
          </div>
        </div>
      )}
    </article>
  );
}
