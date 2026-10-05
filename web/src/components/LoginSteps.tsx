import type { ReactNode } from "react";

import { useLocale, type Locale } from "../i18n/locale";
import { useMessages } from "../i18n/messages";
import { HOME_PATH, type Role } from "../routes";
import type { DemoMailbox } from "../session/demoCode";
import type { SessionAnswer } from "../session/login";
import { CodeStep, type CodeSent } from "./CodeStep";
import { IdentityForm } from "./IdentityForm";

export type SentTo<Identity> = CodeSent & { identity: Identity };

type LoginStepsProps<Identity> = {
  role: Role;
  typed: Identity | null;
  sent: SentTo<Identity> | null;
  onSentChange: (sent: SentTo<Identity> | null) => void;
  identityRows: (identity: Identity) => { label: string; value: string }[];
  demoMailbox: (identity: Identity) => DemoMailbox;
  requestCode: (identity: Identity, locale: Locale) => Promise<number | null>;
  openSession: (identity: Identity, code: string) => Promise<SessionAnswer>;
  children: ReactNode;
};

export function LoginSteps<Identity>({
  role,
  typed,
  sent,
  onSentChange,
  identityRows,
  demoMailbox,
  requestCode,
  openSession,
  children,
}: LoginStepsProps<Identity>) {
  const locale = useLocale();
  const t = useMessages();

  if (sent) {
    const { identity } = sent;
    return (
      <CodeStep
        identity={identityRows(identity)}
        demoMailbox={demoMailbox(identity)}
        sent={sent}
        changeLabel={t.login[role].change}
        home={HOME_PATH[role]}
        requestCode={() => requestCode(identity, locale)}
        openSession={(code) => openSession(identity, code)}
        onResent={(next) => onSentChange({ ...sent, ...next })}
        onChangeIdentity={() => onSentChange(null)}
      />
    );
  }

  const send = async () => (typed === null ? null : requestCode(typed, locale));
  const markSent = (expiresInSeconds: number) => {
    if (typed !== null) {
      onSentChange({ identity: typed, expiresInSeconds, resent: false });
    }
  };
  return (
    <IdentityForm ready={typed !== null} requestCode={send} onSent={markSent}>
      {children}
    </IdentityForm>
  );
}
