import type { ReactNode } from "react";

type AppBarProps = {
  firstName?: string;
  onSignOut?: () => void;
  tools?: ReactNode;
};

export function AppBar({ firstName, onSignOut, tools }: AppBarProps) {
  return (
    <header className="appbar glass">
      <div className="appbar-in">
        <span className="brand">
          <span className="orb" aria-hidden="true" />
          Alba
        </span>
        {(tools || onSignOut) && (
          <div className="appbar-actions">
            {tools}
            {firstName && <span className="name-pill glass">{firstName}</span>}
            {onSignOut && (
              <button type="button" className="btn text" onClick={onSignOut}>
                Salir
              </button>
            )}
          </div>
        )}
      </div>
    </header>
  );
}
