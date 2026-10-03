import { useNavigate } from "react-router";

import { useMessages } from "../i18n/messages";
import { LOGIN_PATH, type Role } from "../routes";
import { signOut } from "../session/session";
import { AppBar } from "./AppBar";

export function SessionEnded({ role }: { role: Role }) {
  const navigate = useNavigate();
  const t = useMessages();

  const signInAgain = () => {
    signOut();
    navigate(LOGIN_PATH[role], { replace: true });
  };

  return (
    <>
      <AppBar />
      <main className="page">
        <section className="center-card solid enter" role="alert">
          <h1 className="heading">{t.sessionEnded.title}</h1>
          <p className="caption muted">
            {t.sessionEnded.lasts} {t.sessionEnded.signInWith[role]}
          </p>
          <button type="button" className="btn primary" onClick={signInAgain}>
            {t.sessionEnded.again}
          </button>
        </section>
      </main>
    </>
  );
}
