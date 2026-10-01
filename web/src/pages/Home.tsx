import { useState } from "react";
import { useNavigate } from "react-router";

import { api } from "../api/client";
import { useLoad } from "../api/useLoad";
import { AppBar } from "../components/AppBar";
import { ErrorCard } from "../components/ErrorCard";
import { LOGIN_PATH } from "../routes";
import { signOut } from "../session/session";

const loadCurrentCustomer = () => api.GET("/me");

export function Home() {
  const navigate = useNavigate();
  const [attempt, setAttempt] = useState(0);
  const me = useLoad(loadCurrentCustomer, attempt);

  const leave = () => {
    signOut();
    navigate(LOGIN_PATH.customer, { replace: true });
  };

  return (
    <>
      <AppBar firstName={me.status === "ready" ? me.data.first_name : undefined} onSignOut={leave} />
      <main className="page">
        {me.status === "loading" && <span className="pulse greeting" aria-label="Cargando" />}
        {me.status === "error" && <ErrorCard message="No pudimos cargar tus datos." onRetry={() => setAttempt((n) => n + 1)} />}
        {me.status === "ready" && (
          <div className="intro enter">
            <h1 className="display">Hola, {me.data.first_name}</h1>
            <p className="lede">Tus productos aparecerán aquí.</p>
          </div>
        )}
      </main>
    </>
  );
}
