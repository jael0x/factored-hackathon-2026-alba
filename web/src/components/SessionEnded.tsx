import { useNavigate } from "react-router";

import { LOGIN_PATH, type Role } from "../routes";
import { signOut } from "../session/session";
import { AppBar } from "./AppBar";

const SIGN_IN_WITH: Record<Role, string> = {
  customer: "Entra de nuevo con tu documento.",
  agent: "Entra de nuevo con tu correo y tu código de empleado.",
};

export function SessionEnded({ role }: { role: Role }) {
  const navigate = useNavigate();

  const signInAgain = () => {
    signOut();
    navigate(LOGIN_PATH[role], { replace: true });
  };

  return (
    <>
      <AppBar />
      <main className="page">
        <section className="center-card solid enter" role="alert">
          <h1 className="heading">Tu sesión terminó</h1>
          <p className="caption muted">La sesión dura 15 minutos y no se renueva sola. {SIGN_IN_WITH[role]}</p>
          <button type="button" className="btn primary" onClick={signInAgain}>
            Volver a entrar
          </button>
        </section>
      </main>
    </>
  );
}
