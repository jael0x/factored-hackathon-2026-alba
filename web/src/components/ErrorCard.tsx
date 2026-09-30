type ErrorCardProps = {
  message: string;
  onRetry: () => void;
};

export function ErrorCard({ message, onRetry }: ErrorCardProps) {
  return (
    <section className="center-card solid enter" role="alert">
      <h2 className="heading">{message}</h2>
      <p className="caption muted">Revisa tu conexión e inténtalo de nuevo.</p>
      <button type="button" className="btn secondary" onClick={onRetry}>
        Reintentar
      </button>
    </section>
  );
}
