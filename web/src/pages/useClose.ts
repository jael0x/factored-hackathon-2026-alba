import { useCallback, useState } from "react";

import { api } from "../api/client";
import type { components } from "../api/schema";
import { closeAnswerOf, isGone, type CloseAnswer, type ConsultantCaseLoad } from "../consultant";

type CloseOutcome = components["schemas"]["CloseOutcome"];

export async function loadConsultantCase(processId: string): Promise<{ data?: ConsultantCaseLoad }> {
  const { data, response } = await api.GET("/consultant/case/{process_id}", {
    params: { path: { process_id: processId } },
  });
  if (data) {
    return { data: { kind: "open", packet: data } };
  }
  return isGone(response.status) ? { data: { kind: "gone" } } : {};
}

// The close body is only the outcome: the customer's locale and the consultant come from the case and the session.
export function useClose(processId: string, onClosed: () => void, onSettled: () => void) {
  const [closing, setClosing] = useState(false);
  const [answer, setAnswer] = useState<CloseAnswer | null>(null);

  const close = useCallback(
    async (outcome: CloseOutcome) => {
      setClosing(true);
      setAnswer(null);
      const result = await api
        .POST("/consultant/case/{process_id}/close", {
          params: { path: { process_id: processId } },
          body: { outcome },
        })
        .catch(() => null);
      setClosing(false);
      const next = closeAnswerOf(result?.response.status ?? null, result?.error?.error);
      setAnswer(next);
      if (next.kind === "closed") {
        onClosed();
      } else if (next.kind === "not_closable" || next.kind === "already_closed" || next.kind === "gone") {
        onSettled();
      }
    },
    [processId, onClosed, onSettled],
  );

  return { closing, answer, close };
}
