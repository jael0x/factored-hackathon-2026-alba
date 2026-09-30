import { useEffect, useId, useState } from "react";

import { api } from "../api/client";
import type { components } from "../api/schema";
import { fullName, lastFour } from "../format";

type Hit = components["schemas"]["CustomerSearchHit"];

type Results =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; hits: Hit[] };

type DemoCustomerSearchProps = {
  titleId: string;
  selectedDocument: string;
  onPick: (documentNumber: string) => void;
  onClose: () => void;
};

const SEARCH_DELAY_MS = 250;

export function DemoCustomerSearch({ titleId, selectedDocument, onPick, onClose }: DemoCustomerSearchProps) {
  const queryId = useId();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Results>({ status: "idle" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const q = query.trim();
    if (q === "") {
      setResults({ status: "idle" });
      return;
    }
    let cancelled = false;
    setResults({ status: "loading" });
    const timer = window.setTimeout(async () => {
      const { data } = await api.GET("/customers/search", { params: { query: { q } } }).catch(() => ({ data: undefined }));
      if (cancelled) {
        return;
      }
      setResults(data ? { status: "ready", hits: data.customers } : { status: "error" });
    }, SEARCH_DELAY_MS);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [query, attempt]);

  const pickRandom = async () => {
    setResults({ status: "loading" });
    const { data } = await api
      .GET("/customers/search", { params: { query: { random: true } } })
      .catch(() => ({ data: undefined }));
    const hit = data?.customers[0];
    if (!hit) {
      setResults({ status: "error" });
      return;
    }
    setResults({ status: "ready", hits: [hit] });
    onPick(hit.document_number);
  };

  return (
    <div className="stack">
      <div className="panel-head popover-head">
        <h2 className="heading" id={titleId}>
          Usuarios de prueba
        </h2>
        <button type="button" className="btn text" onClick={onClose}>
          Cerrar
        </button>
      </div>
      <div className="stack">
        <p className="caption muted">
          Solo en el demo. Elegir a alguien llena su documento y cierra este panel; el código igual llega por correo.
        </p>
        <div>
          <label className="field-label" htmlFor={queryId}>
            Nombre, documento o número de cliente
          </label>
          <div className="field-wrap">
            <svg className="i" viewBox="0 0 24 24" aria-hidden="true">
              <circle cx="11" cy="11" r="6" />
              <path d="M20 20l-4.5-4.5" />
            </svg>
            <input
              id={queryId}
              className="field"
              type="search"
              autoFocus
              autoComplete="off"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>
        </div>
        <SearchResults results={results} selectedDocument={selectedDocument} onPick={onPick} onRetry={() => setAttempt((n) => n + 1)} />
        <div className="actions-row">
          <button type="button" className="btn secondary" onClick={pickRandom}>
            Elegir al azar
          </button>
        </div>
      </div>
    </div>
  );
}

type SearchResultsProps = {
  results: Results;
  selectedDocument: string;
  onPick: (documentNumber: string) => void;
  onRetry: () => void;
};

function SearchResults({ results, selectedDocument, onPick, onRetry }: SearchResultsProps) {
  if (results.status === "idle") {
    return null;
  }
  if (results.status === "loading") {
    return <span className="pulse" aria-label="Buscando" />;
  }
  if (results.status === "error") {
    return (
      <div className="actions-row" role="alert">
        <p className="error-line">No pudimos buscar.</p>
        <button type="button" className="btn text" onClick={onRetry}>
          Reintentar
        </button>
      </div>
    );
  }
  if (results.hits.length === 0) {
    return <p className="empty caption muted solid results">Nadie coincide con esa búsqueda.</p>;
  }
  return (
    <ul className="results solid" aria-label="Resultados">
      {results.hits.map((hit) => (
        <li key={hit.customer_id}>
          <button type="button" aria-pressed={hit.document_number === selectedDocument} onClick={() => onPick(hit.document_number)}>
            <span className="grow">
              <span className="name">{fullName(hit)}</span>
              <br />
              <span className="caption muted">
                {hit.country} · documento <span aria-label={`terminado en ${lastFour(hit.document_number)}`}>••••{lastFour(hit.document_number)}</span>
              </span>
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
