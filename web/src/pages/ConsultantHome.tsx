import { useState } from "react";
import { useNavigate } from "react-router";

import { api } from "../api/client";
import { useLoad } from "../api/useLoad";
import { AppBar } from "../components/AppBar";
import { ErrorCard } from "../components/ErrorCard";
import { useMessages } from "../i18n/messages";
import { LOGIN_PATH } from "../routes";
import { signOut } from "../session/session";

const loadCurrentConsultant = () => api.GET("/consultant/me");

export function ConsultantHome() {
  const navigate = useNavigate();
  const [attempt, setAttempt] = useState(0);
  const me = useLoad(loadCurrentConsultant, attempt);
  const t = useMessages();

  const leave = () => {
    signOut();
    navigate(LOGIN_PATH.consultant, { replace: true });
  };

  return (
    <>
      <AppBar firstName={me.status === "ready" ? me.data.first_name : undefined} onSignOut={leave} />
      <main className="page">
        {me.status === "loading" && <span className="pulse greeting" aria-label={t.loading} />}
        {me.status === "error" && <ErrorCard message={t.consultantHome.loadFailed} onRetry={() => setAttempt((n) => n + 1)} />}
        {me.status === "ready" && (
          <div className="intro enter">
            <h1 className="display">{t.home.greeting(me.data.first_name)}</h1>
            <p className="lede">{t.consultantHome.lede}</p>
            <p className="caption muted">
              {me.data.specialty && `${me.data.specialty} · `}
              {t.consultantHome.employee} <span className="mono">{me.data.employee_code}</span>
            </p>
          </div>
        )}
      </main>
    </>
  );
}
