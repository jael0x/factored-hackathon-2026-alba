import { useNavigate } from "react-router";

import { signOut } from "../session/session";
import { AppBar } from "./AppBar";

export function SessionEnded() {
  const navigate = useNavigate();

  const signInAgain = () => {
    signOut();
    navigate("/login", { replace: true });
  };

  return (
    <>
      <AppBar />
      <main className="page">
        <section className="center-card solid enter" role="alert">
          <h1 className="heading">Tu sesión terminó</h1>
          <p className="caption muted">La sesión dura 15 minutos y no se renueva sola. Entra de nuevo con tu documento.</p>
          <button type="button" className="btn primary" onClick={signInAgain}>
            Volver a entrar
          </button>
        </section>
      </main>
    </>
  );
}
