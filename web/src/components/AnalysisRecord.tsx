import type { components } from "../api/schema";
import { useMessages } from "../i18n/messages";
import { factRows, ruleRows, type FactRow } from "../trace";
import { TracePart } from "./TraceDetail";

type AnalysisCompleted = components["schemas"]["TraceAnalysisCompleted"];

export function AnalysisRecord({ analysis }: { analysis: AnalysisCompleted }) {
  const t = useMessages();
  const facts = factRows(analysis.facts);
  return (
    <div className="trace-analysis">
      <p className="caption">
        {t.trace.policy} <span className="mono">{analysis.policy_version}</span>
      </p>
      <h3 className="kicker">{t.trace.rules}</h3>
      <ol className="trace-rules">
        {ruleRows(analysis.rule_trace).map((row) => (
          <li key={row.rule}>
            <span className="mono">{row.rule}</span>
            <TracePart part={row.result} />
            <span className="mono muted trace-input">
              {row.inputs.map((input) => `${input.name}=${input.value}`).join(" ")}
            </span>
          </li>
        ))}
      </ol>
      {facts.length > 0 && <FactsTable facts={facts} />}
    </div>
  );
}

function FactsTable({ facts }: { facts: readonly FactRow[] }) {
  const t = useMessages();
  return (
    <>
      <h3 className="kicker">{t.trace.facts}</h3>
      <div className="table-scroll">
        <table className="trace-facts">
          <thead>
            <tr>
              <th scope="col">{t.trace.columns.name}</th>
              <th scope="col">{t.trace.columns.value}</th>
              <th scope="col">{t.trace.columns.source}</th>
              <th scope="col">{t.trace.columns.asOf}</th>
            </tr>
          </thead>
          <tbody>
            {facts.map((fact) => (
              <tr key={fact.name}>
                <td className="mono">{fact.name}</td>
                <td className="num">{fact.value}</td>
                <td className="mono">{fact.source}</td>
                <td className="num">{fact.asOf}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
