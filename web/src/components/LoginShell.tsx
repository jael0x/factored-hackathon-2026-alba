import { useId, type ReactNode } from "react";
import { Navigate } from "react-router";

import { api } from "../api/client";
import { useLoad } from "../api/useLoad";
import { HOME_PATH, type Role } from "../routes";
import { useSession } from "../session/session";
import { AppBar } from "./AppBar";

const loadConfig = () => api.GET("/config");

type LoginShellProps = {
  role: Role;
  title: string;
  lede: string;
  notice: string;
  panelTitle: string;
  demo: ReactNode;
  children: ReactNode;
};

export function LoginShell({ role, title, lede, notice, panelTitle, demo, children }: LoginShellProps) {
  const panelTitleId = useId();
  const session = useSession();
  const config = useLoad(loadConfig);

  if (session.status === "active" && session.session.role === role) {
    return <Navigate to={HOME_PATH[role]} replace />;
  }

  const showDemo = config.status === "ready" && config.data.demo_login;

  return (
    <>
      <AppBar tools={showDemo ? demo : undefined} />
      <main className="page login-layout">
        <div className="intro">
          <h1 className="display">{title}</h1>
          <p className="lede">{lede}</p>
          <p className="notice">{notice}</p>
          {config.status === "error" && <p className="caption muted">No pudimos leer la configuración del demo.</p>}
        </div>
        <div className="login-form">
          <section className="panel glass" aria-labelledby={panelTitleId}>
            <div className="panel-head">
              <h2 className="heading" id={panelTitleId}>
                {panelTitle}
              </h2>
            </div>
            {children}
          </section>
        </div>
      </main>
    </>
  );
}
