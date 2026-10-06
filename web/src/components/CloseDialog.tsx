import { useEffect, useId, useRef, type SyntheticEvent } from "react";

import type { components } from "../api/schema";
import { PREQUALIFIED } from "../chat";
import { useMessages } from "../i18n/messages";

type CloseOutcome = components["schemas"]["CloseOutcome"];

type CloseDialogProps = {
  outcome: CloseOutcome | null;
  customerName: string;
  closing: boolean;
  onConfirm: (outcome: CloseOutcome) => void;
  onCancel: () => void;
};

// DESIGN.md "Consultant case": the review before the close, with "Volver" focused first.
export function CloseDialog({ outcome, customerName, closing, onConfirm, onCancel }: CloseDialogProps) {
  const t = useMessages();
  const titleId = useId();
  const dialog = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const element = dialog.current;
    if (element === null) {
      return;
    }
    if (outcome !== null && !element.open) {
      element.showModal();
    } else if (outcome === null && element.open) {
      element.close();
    }
  }, [outcome]);

  const holdWhileClosing = (event: SyntheticEvent) => {
    if (closing) {
      event.preventDefault();
    }
  };

  return (
    <dialog
      ref={dialog}
      className="close-dialog solid"
      aria-labelledby={titleId}
      onCancel={holdWhileClosing}
      onClose={onCancel}
    >
      {outcome !== null && (
        <div className="stack">
          <span className={`state-tag ${outcome === PREQUALIFIED ? "green" : "stop"}`}>
            {t.consultant.closeTag[outcome]}
          </span>
          <h2 className="heading" id={titleId}>
            {t.consultant.closeTitle}
          </h2>
          <p>{t.consultant.confirmText(customerName)}</p>
          <div className="actions-row end">
            <button type="button" className="btn secondary" autoFocus disabled={closing} onClick={onCancel}>
              {t.consultant.back}
            </button>
            <button type="button" className="btn decisive" disabled={closing} onClick={() => onConfirm(outcome)}>
              {closing ? t.consultant.closing : t.consultant.confirm}
            </button>
          </div>
        </div>
      )}
    </dialog>
  );
}
