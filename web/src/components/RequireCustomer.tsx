import type { ReactNode } from "react";
import { Navigate } from "react-router";

import { useSession } from "../session/session";
import { SessionEnded } from "./SessionEnded";

export function RequireCustomer({ children }: { children: ReactNode }) {
  const session = useSession();
  if (session.status === "ended") {
    return <SessionEnded />;
  }
  if (session.status === "signed_out" || session.session.role !== "customer") {
    return <Navigate to="/login" replace />;
  }
  return children;
}
