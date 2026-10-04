import { useMessages } from "../i18n/messages";

type ErrorCardProps = {
  message: string;
  onRetry: () => void;
};

export function ErrorCard({ message, onRetry }: ErrorCardProps) {
  const t = useMessages();
  return (
    <section className="center-card solid enter" role="alert">
      <h2 className="heading">{message}</h2>
      <p className="caption muted">{t.checkConnection}</p>
      <button type="button" className="btn secondary" onClick={onRetry}>
        {t.retry}
      </button>
    </section>
  );
}
