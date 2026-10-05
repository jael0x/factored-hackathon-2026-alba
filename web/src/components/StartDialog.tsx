import { useEffect, useId, useRef } from "react";

import type { components } from "../api/schema";
import { useMessages } from "../i18n/messages";

type ProductKey = components["schemas"]["ProductKey"];

type StartDialogProps = {
  product: ProductKey | null;
  onBegin: (product: ProductKey) => void;
  onCancel: () => void;
};

// The consent before a case starts (PLAN.md D24): it names the product, the policy, and that it is a simulation.
export function StartDialog({ product, onBegin, onCancel }: StartDialogProps) {
  const t = useMessages();
  const titleId = useId();
  const dialog = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const element = dialog.current;
    if (element === null) {
      return;
    }
    if (product !== null && !element.open) {
      element.showModal();
    } else if (product === null && element.open) {
      element.close();
    }
  }, [product]);

  const named = product === null ? "" : t.chat.product[product];
  return (
    <dialog ref={dialog} className="start-dialog solid" aria-labelledby={titleId} onClose={onCancel}>
      {product !== null && (
        <div className="stack">
          <h2 className="heading" id={titleId}>
            {t.start.title} <strong>{named}</strong>
          </h2>
          <p>
            {t.start.lead} <strong>{named}</strong> {t.start.rest}
          </p>
          <div className="actions-row end">
            <button type="button" className="btn secondary" onClick={onCancel}>
              {t.start.cancel}
            </button>
            <button type="button" className="btn primary" onClick={() => onBegin(product)}>
              {t.start.begin}
            </button>
          </div>
        </div>
      )}
    </dialog>
  );
}
