import { useEffect, useState } from "react";

export type Loaded<T> = { status: "loading" } | { status: "error" } | { status: "ready"; data: T };

export function useLoad<T>(load: () => Promise<{ data?: T }>, attempt = 0): Loaded<T> {
  const [state, setState] = useState<Loaded<T>>({ status: "loading" });
  useEffect(() => {
    let cancelled = false;
    setState({ status: "loading" });
    load()
      .then(({ data }) => {
        if (!cancelled) {
          setState(data === undefined ? { status: "error" } : { status: "ready", data });
        }
      })
      .catch(() => {
        if (!cancelled) {
          setState({ status: "error" });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [load, attempt]);
  return state;
}
