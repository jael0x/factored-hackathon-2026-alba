import { useEffect, useState } from "react";

type HealthState = "loading" | "ok" | "error";

export function App() {
  const [health, setHealth] = useState<HealthState>("loading");
  const [detail, setDetail] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetch("/api/health")
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const body = (await response.json()) as { status?: string };
        if (!cancelled) {
          setHealth(body.status === "ok" ? "ok" : "error");
          setDetail(body.status ?? "");
        }
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
