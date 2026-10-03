import type { ReactNode } from "react";

import { useMessages } from "../i18n/messages";
import { LanguageSwitch } from "./LanguageSwitch";

type AppBarProps = {
  firstName?: string;
  onSignOut?: () => void;
  tools?: ReactNode;
};

export function AppBar({ firstName, onSignOut, tools }: AppBarProps) {
  const t = useMessages();
  return (
    <header className="appbar glass">
      <div className="appbar-in">
        <span className="brand">
          <span className="orb" aria-hidden="true" />
          Alba
        </span>
        <div className="appbar-actions">
          {tools}
          <LanguageSwitch />
          {firstName && <span className="name-pill glass">{firstName}</span>}
          {onSignOut && (
            <button type="button" className="btn text" onClick={onSignOut}>
              {t.signOut}
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
