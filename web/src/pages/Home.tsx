import { useEffect, useState } from "react";
import { useNavigate } from "react-router";

import { api } from "../api/client";
import type { components } from "../api/schema";
import { AppBar } from "../components/AppBar";
import { ErrorCard } from "../components/ErrorCard";
import { signOut } from "../session/session";

type CurrentCustomer = components["schemas"]["CurrentCustomer"];

type Me = { status: "loading" } | { status: "error" } | { status: "ready"; customer: CurrentCustomer };

export function Home() {
  const navigate = useNavigate();
  const [attempt, setAttempt] = useState(0);
  const me = useCurrentCustomer(attempt);

  const leave = () => {
    signOut();
    navigate("/login", { replace: true });
  };

  return (
    <>
      <AppBar firstName={me.status === "ready" ? me.customer.first_name : undefined} onSignOut={leave} />
      <main className="page">
        {me.status === "loading" && <span className="pulse greeting" aria-label="Cargando" />}
        {me.status === "error" && <ErrorCard message="No pudimos cargar tus datos." onRetry={() => setAttempt((n) => n + 1)} />}
        {me.status === "ready" && (
          <div className="intro enter">
            <h1 className="display">Hola, {me.customer.first_name}</h1>
            <p className="lede">Tus productos aparecerán aquí.</p>
          </div>
        )}
      </main>
    </>
  );
}

function useCurrentCustomer(attempt: number): Me {
  const [me, setMe] = useState<Me>({ status: "loading" });
  useEffect(() => {
    let cancelled = false;
    setMe({ status: "loading" });
    api
      .GET("/me")
      .then(({ data }) => {
        if (!cancelled) {
          setMe(data ? { status: "ready", customer: data } : { status: "error" });
        }
      })
      .catch(() => {
        if (!cancelled) {
          setMe({ status: "error" });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [attempt]);
  return me;
}
