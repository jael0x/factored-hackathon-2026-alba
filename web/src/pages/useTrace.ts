import { useCallback, useState } from "react";

import { api } from "../api/client";
import type { components } from "../api/schema";
import { NOT_FOUND } from "../api/status";
import { useLoad } from "../api/useLoad";

type CaseTrace = components["schemas"]["CaseTrace"];

// The trace is read for any case that exists; a 404 means no process has this id.
export type TraceLoad = { kind: "found"; trace: CaseTrace } | { kind: "unknown" };

export async function loadTrace(processId: string): Promise<{ data?: TraceLoad }> {
  const { data, response } = await api.GET("/consultant/case/{process_id}/trace", {
    params: { path: { process_id: processId } },
  });
  if (data) {
    return { data: { kind: "found", trace: data } };
  }
  return response.status === NOT_FOUND ? { data: { kind: "unknown" } } : {};
}

export function useTrace(processId: string) {
  const [attempt, setAttempt] = useState(0);
  const load = useCallback(() => loadTrace(processId), [processId]);
  const trace = useLoad(load, attempt);
  const reload = useCallback(() => setAttempt((n) => n + 1), []);
  return { trace, reload };
}
