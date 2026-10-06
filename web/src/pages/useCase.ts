import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";

import { api } from "../api/client";
import { CONFLICT } from "../api/status";
import type { components } from "../api/schema";
import type { PendingSend } from "../chat";
import { isLocale, useLocale } from "../i18n/locale";
import { HOME_PATH, casePath } from "../routes";

export type CaseData = components["schemas"]["Case"];

// What the home hands over when a product row opens the chat, or what a send hands to the case's own URL.
export type Arrival = { opening?: PendingSend; case?: CaseData };

export function arrivalOf(state: unknown): Arrival {
  if (typeof state !== "object" || state === null) {
    return {};
  }
  const opening = "opening" in state && isPendingSend(state.opening) ? state.opening : undefined;
  const arrived = "case" in state && isCase(state.case) ? state.case : undefined;
  return { opening, case: arrived };
}

function isPendingSend(value: unknown): value is PendingSend {
  return (
    typeof value === "object" &&
    value !== null &&
    "text" in value &&
    typeof value.text === "string" &&
    "clientMessageId" in value &&
    typeof value.clientMessageId === "string" &&
    "locale" in value &&
    isLocale(value.locale)
  );
}

function isCase(value: unknown): value is CaseData {
  return (
    typeof value === "object" &&
    value !== null &&
    "process_id" in value &&
    typeof value.process_id === "string" &&
    "messages" in value &&
    Array.isArray(value.messages)
  );
}

export function useCase(processId: string | undefined, arrived: CaseData | undefined) {
  const [caseData, setCaseData] = useState<CaseData | null>(arrived ?? null);
  const [loadFailed, setLoadFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const reload = useCallback(() => setAttempt((n) => n + 1), []);

  useEffect(() => {
    if (processId === undefined || (caseData?.process_id === processId && attempt === 0)) {
      return;
    }
    let cancelled = false;
    setLoadFailed(false);
    api
      .GET("/case/{process_id}", {
        params: { path: { process_id: processId } },
      })
      .then(({ data }) => {
        if (!cancelled) {
          if (data) {
            setCaseData(data);
          } else {
            setLoadFailed(true);
          }
        }
      })
      .catch(() => !cancelled && setLoadFailed(true));
    return () => {
      cancelled = true;
    };
  }, [processId, caseData?.process_id, attempt]);

  const loading = processId !== undefined && caseData?.process_id !== processId && !loadFailed;
  return { caseData, setCaseData, loading, loadFailed, reload };
}

type Answer = { case: CaseData } | { refused: number | null };

// A start names its product; any other message names its case (D24).
async function postMessage(message: PendingSend, processId: string | undefined): Promise<Answer> {
  const sent = {
    text: message.text,
    client_message_id: message.clientMessageId,
    locale: message.locale,
  };
  const body = message.product ? { ...sent, product: message.product } : { ...sent, process_id: processId };
  const result = await api.POST("/messages", { body }).catch(() => null);
  if (result?.data) {
    return { case: result.data };
  }
  return { refused: result?.response.status ?? null };
}

// A refusal other than a conflict, 503 cycle_pending included, keeps the bubble for a retry with the same id.
export function useSend(processId: string | undefined, onCase: (answer: CaseData) => void, reload: () => void) {
  const navigate = useNavigate();
  const [pending, setPending] = useState<PendingSend | null>(null);
  const [failed, setFailed] = useState(false);

  const send = useCallback(
    async (message: PendingSend): Promise<boolean> => {
      setPending(message);
      setFailed(false);
      const answer = await postMessage(message, processId);
      if ("refused" in answer) {
        if (answer.refused !== CONFLICT) {
          setFailed(true);
          return false;
        }
        // The product already has a case, or this one has ended: the home or a fresh read shows which.
        setPending(null);
        if (message.product) {
          navigate(HOME_PATH.customer, { replace: true });
        } else {
          reload();
        }
        return false;
      }
      setPending(null);
      onCase(answer.case);
      if (answer.case.process_id !== processId) {
        navigate(casePath(answer.case.process_id), {
          replace: true,
          state: { case: answer.case },
        });
      }
      return true;
    },
    [navigate, processId, onCase, reload],
  );

  return { pending, failed, send };
}

// The message a product row hands over is sent once, when the chat opens with no case yet.
export function useOpening(
  processId: string | undefined,
  opening: PendingSend | undefined,
  send: (message: PendingSend) => Promise<boolean>,
) {
  const opened = useRef(false);
  useEffect(() => {
    if (processId === undefined && opening && !opened.current) {
      opened.current = true;
      void send(opening);
    }
  }, [processId, opening, send]);
}

// The API says whether the case can go to a person (Case.appealable, D25); the screen only asks.
export function useAppeal(processId: string | undefined, onCase: (answer: CaseData) => void) {
  const locale = useLocale();
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  const appeal = useCallback(async () => {
    if (processId === undefined) {
      return;
    }
    setBusy(true);
    setFailed(false);
    const { data } = await api
      .POST("/case/{process_id}/appeal", {
        params: { path: { process_id: processId } },
        body: { locale },
      })
      .catch(() => ({ data: undefined }));
    setBusy(false);
    if (data) {
      onCase(data);
    } else {
      setFailed(true);
    }
  }, [processId, locale, onCase]);

  return { busy, failed, appeal };
}
