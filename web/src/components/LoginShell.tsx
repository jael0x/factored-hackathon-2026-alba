import { useId, type ReactNode } from "react";
import { Link, Navigate } from "react-router";

import { api } from "../api/client";
import { useLoad } from "../api/useLoad";
import { useMessages } from "../i18n/messages";
import { HOME_PATH, LOGIN_PATH, type Role } from "../routes";
import { useSession } from "../session/session";
import { AppBar } from "./AppBar";

const loadConfig = () => api.GET("/config");

const OTHER_LOGIN: Record<Role, string> = { customer: LOGIN_PATH.consultant, consultant: LOGIN_PATH.customer };

type LoginShellProps = {
  role: Role;
  codeSent: boolean;
  demo: ReactNode;
  children: ReactNode;
};

export function LoginShell({ role, codeSent, demo, children }: LoginShellProps) {
  const panelTitleId = useId();
  const session = useSession();
  const config = useLoad(loadConfig);
  const t = useMessages();

  if (session.status === "active" && session.session.role === role) {
    return <Navigate to={HOME_PATH[role]} replace />;
  }

  const showDemo = config.status === "ready" && config.data.demo_login;
  const copy = t.login[role];
  return (
    <>
      <AppBar tools={showDemo ? demo : undefined} />
      <main className="page login-layout">
        <div className="intro">
          <h1 className="display">{copy.title}</h1>
          <p className="lede">{copy.lede}</p>
          <p className="notice">{copy.notice}</p>
          {config.status === "error" && <p className="caption muted">{t.login.demoConfigFailed}</p>}
        </div>
        <div className="login-form">
          <section className="panel glass" aria-labelledby={panelTitleId}>
            <div className="panel-head">
              <h2 className="heading" id={panelTitleId}>
                {codeSent ? t.login.yourCode : copy.panelTitle}
              </h2>
            </div>
            {children}
          </section>
          <Link className="btn text centered" to={OTHER_LOGIN[role]}>
            {copy.otherLogin}
          </Link>
        </div>
      </main>
    </>
  );
}
