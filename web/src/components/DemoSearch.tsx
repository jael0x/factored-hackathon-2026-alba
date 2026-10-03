import { useEffect, useId, useState, type ReactNode } from "react";

import { useMessages } from "../i18n/messages";

export type DemoSource<Hit> = {
  heading: string;
  help: string;
  queryLabel: string;
  search: (q: string) => Promise<Hit[] | null>;
  pickRandom: () => Promise<Hit | null>;
  key: (hit: Hit) => string;
  render: (hit: Hit) => ReactNode;
};

type Results<Hit> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; hits: Hit[] };

type DemoSearchProps<Hit> = {
  titleId: string;
  source: DemoSource<Hit>;
  isSelected: (hit: Hit) => boolean;
  onPick: (hit: Hit) => void;
  onClose: () => void;
};

const SEARCH_DELAY_MS = 250;

export function DemoSearch<Hit>({ titleId, source, isSelected, onPick, onClose }: DemoSearchProps<Hit>) {
  const queryId = useId();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Results<Hit>>({ status: "idle" });
  const [attempt, setAttempt] = useState(0);
  const { search, pickRandom } = source;
  const t = useMessages();

  useEffect(() => {
    const q = query.trim();
    if (q === "") {
      setResults({ status: "idle" });
      return;
    }
    let cancelled = false;
    setResults({ status: "loading" });
    const timer = window.setTimeout(async () => {
      const hits = await search(q);
      if (cancelled) {
        return;
      }
      setResults(hits ? { status: "ready", hits } : { status: "error" });
    }, SEARCH_DELAY_MS);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [query, attempt, search]);

  const pickAtRandom = async () => {
    setResults({ status: "loading" });
    const hit = await pickRandom();
    if (hit === null) {
      setResults({ status: "error" });
      return;
    }
    setResults({ status: "ready", hits: [hit] });
    onPick(hit);
  };

  return (
    <div className="stack">
      <div className="panel-head popover-head">
        <h2 className="heading" id={titleId}>
          {source.heading}
        </h2>
        <button type="button" className="btn text" onClick={onClose}>
          {t.demo.close}
        </button>
      </div>
      <div className="stack">
        <p className="caption muted">{source.help}</p>
        <div>
          <label className="field-label" htmlFor={queryId}>
            {source.queryLabel}
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
        <SearchResults
          results={results}
          source={source}
          isSelected={isSelected}
          onPick={onPick}
          onRetry={() => setAttempt((n) => n + 1)}
        />
        <div className="actions-row">
          <button type="button" className="btn secondary" onClick={pickAtRandom}>
            {t.demo.pickRandom}
          </button>
        </div>
      </div>
    </div>
  );
}

type SearchResultsProps<Hit> = {
  results: Results<Hit>;
  source: DemoSource<Hit>;
  isSelected: (hit: Hit) => boolean;
  onPick: (hit: Hit) => void;
  onRetry: () => void;
};

function SearchResults<Hit>({ results, source, isSelected, onPick, onRetry }: SearchResultsProps<Hit>) {
  const t = useMessages();
  if (results.status === "idle") {
    return null;
  }
  if (results.status === "loading") {
    return <span className="pulse" aria-label={t.demo.searching} />;
  }
  if (results.status === "error") {
    return (
      <div className="actions-row" role="alert">
        <p className="error-line">{t.demo.searchFailed}</p>
        <button type="button" className="btn text" onClick={onRetry}>
          {t.retry}
        </button>
      </div>
    );
  }
  if (results.hits.length === 0) {
    return <p className="empty caption muted solid results">{t.demo.noMatch}</p>;
  }
  return (
    <ul className="results solid" aria-label={t.demo.results}>
      {results.hits.map((hit) => (
        <li key={source.key(hit)}>
          <button type="button" aria-pressed={isSelected(hit)} onClick={() => onPick(hit)}>
            <span className="grow">{source.render(hit)}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}
