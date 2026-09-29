import { useEffect, useState } from "react";

import { api } from "./api/client";

type HealthState = "loading" | "ok" | "error";

export function App() {
  const [health, setHealth] = useState<HealthState>("loading");
  const [detail, setDetail] = useState("");

  useEffect(() => {
    let cancelled = false;
    api
      .GET("/health")
      .then((result) => {
        if (cancelled) {
          return;
        }
        if (result.data) {
          setHealth("ok");
          setDetail(result.data.status);
          return;
        }
        setHealth("error");
        setDetail(`HTTP ${result.response.status}`);
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setHealth("error");
          setDetail(error instanceof Error ? error.message : "unknown error");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="page">
      <p className="brand">Alba</p>
      <h1>Precalificación de crédito</h1>
      <p className="lede">
        Stack local listo. El chat y la policy llegan en los siguientes incrementos.
      </p>
      <p className={`status status-${health}`}>
        API: {health === "loading" ? "conectando…" : health === "ok" ? "ok" : `error (${detail})`}
      </p>
    </main>
  );
}
