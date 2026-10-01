import type { ReactNode } from "react";
import { Navigate } from "react-router";

import { LOGIN_PATH, type Role } from "../routes";
import { useSession } from "../session/session";
import { SessionEnded } from "./SessionEnded";

export function RequireSession({ role, children }: { role: Role; children: ReactNode }) {
  const session = useSession();
  if (session.status === "ended") {
    return <SessionEnded role={role} />;
  }
  if (session.status === "signed_out" || session.session.role !== role) {
    return <Navigate to={LOGIN_PATH[role]} replace />;
  }
  return children;
}
