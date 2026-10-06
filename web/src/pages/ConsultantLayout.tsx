import { createContext, useCallback, useContext, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router";

import { api } from "../api/client";
import type { components } from "../api/schema";
import { useLoad, type Loaded } from "../api/useLoad";
import { LanguageSwitch } from "../components/LanguageSwitch";
import { fullName } from "../format";
import { useMessages } from "../i18n/messages";
import { HOME_PATH, LOGIN_PATH } from "../routes";
import { signOut } from "../session/session";

type QueueItem = components["schemas"]["ConsultantQueueItem"];
type CurrentConsultant = components["schemas"]["CurrentConsultant"];

type ConsultantShell = { queue: Loaded<QueueItem[]>; reloadQueue: () => void };

const ShellContext = createContext<ConsultantShell | null>(null);

const loadMe = () => api.GET("/consultant/me");

async function loadQueue() {
  const { data } = await api.GET("/consultant/queue");
  return { data: data?.cases };
}

// The session's level owns the consultant and the queue: the sidebar count and the queue page read one fetch.
export function ConsultantLayout() {
  const navigate = useNavigate();
  const t = useMessages();
  const [meAttempt, setMeAttempt] = useState(0);
  const me = useLoad(loadMe, meAttempt);
  const [queueAttempt, setQueueAttempt] = useState(0);
  const queue = useLoad(loadQueue, queueAttempt);
  const reloadQueue = useCallback(() => setQueueAttempt((n) => n + 1), []);

  const leave = () => {
    signOut();
    navigate(LOGIN_PATH.consultant, { replace: true });
  };

  return (
    <div className="console">
      <nav className="sidebar glass" aria-label={t.consultant.nav}>
        <span className="brand">
          <span className="orb" aria-hidden="true" />
          Alba
        </span>
        <NavLink to={HOME_PATH.consultant} className="nav-item">
          <svg className="i" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M4 13l2-7h12l2 7" />
            <path d="M4 13v5h16v-5" />
            <path d="M4 13h5l1 2h4l1-2h5" />
          </svg>
          <span className="grow">{t.consultant.queue}</span>
          {queue.status === "ready" && <CaseCount count={queue.data.length} />}
        </NavLink>
        <div className="sidebar-foot">
          <Profile me={me} onRetry={() => setMeAttempt((n) => n + 1)} />
          <div className="sidebar-actions">
            <LanguageSwitch />
            <button type="button" className="btn text" onClick={leave}>
              {t.signOut}
            </button>
          </div>
        </div>
      </nav>
      <main className="console-main">
        <ShellContext.Provider value={{ queue, reloadQueue }}>
          <Outlet />
        </ShellContext.Provider>
      </main>
    </div>
  );
}

export function useConsultantShell(): ConsultantShell {
  const shell = useContext(ShellContext);
  if (shell === null) {
    throw new Error("a consultant page renders inside ConsultantLayout");
  }
  return shell;
}

export function CaseCount({ count }: { count: number }) {
  const t = useMessages();
  return (
    <span className="count" aria-label={t.consultant.caseCount(count)}>
      {count}
    </span>
  );
}

function Profile({ me, onRetry }: { me: Loaded<CurrentConsultant>; onRetry: () => void }) {
  const t = useMessages();
  if (me.status === "loading") {
    return <span className="pulse profile-slot" aria-label={t.loading} />;
  }
  if (me.status === "error") {
    return (
      <div className="profile" role="alert">
        <p className="caption">{t.consultant.loadFailed}</p>
        <button type="button" className="btn text" onClick={onRetry}>
          {t.retry}
        </button>
      </div>
    );
  }
  return (
    <div className="profile">
      <div className="label">{fullName(me.data)}</div>
      <div className="caption muted">
        {me.data.specialty && `${me.data.specialty} · `}
        {t.consultant.employee} <span className="mono">{me.data.employee_code}</span>
      </div>
    </div>
  );
}
