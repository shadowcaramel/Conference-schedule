import clsx from "clsx";
import type { Diagnostics, Programme } from "./types";
import { mentionsId, sessionLabel, textOf } from "./text";

type Props = {
  diagnostics: Diagnostics;
  programme: Programme;
  displayLanguages: string[];
  activeId: string | null;
  onOpenMessage: (message: string) => void;
};

function quotedData(message: string, programme: Programme, languages: string[]): string | null {
  const contribution = programme.contributions
    .filter((item) => mentionsId(message, item.id))
    .sort((a, b) => b.id.length - a.id.length)[0];
  if (contribution) {
    return textOf(contribution.title, languages) || null;
  }
  const session = programme.sessions
    .filter((item) => mentionsId(message, item.id))
    .sort((a, b) => b.id.length - a.id.length)[0];
  if (session) {
    return sessionLabel(session, programme, languages);
  }
  return null;
}

export function DiagnosticsList({ diagnostics, programme, displayLanguages, activeId, onOpenMessage }: Props) {
  const rows = [
    ...diagnostics.errors.map((message) => ({ level: "error" as const, message })),
    ...diagnostics.warnings.map((message) => ({ level: "warning" as const, message })),
  ];

  return (
    <section className="checks" aria-label="Validation">
      <header className="detail-head">
        <h2>Checks</h2>
        <p className="meta">
          {diagnostics.errors.length} {diagnostics.errors.length === 1 ? "error" : "errors"}
          {" · "}
          {diagnostics.warnings.length} {diagnostics.warnings.length === 1 ? "warning" : "warnings"}
        </p>
      </header>
      {rows.length === 0 ? (
        <p className="quiet">No errors or warnings.</p>
      ) : (
        <ul className="check-list">
          {rows.map((row, index) => {
            const current = activeId ? mentionsId(row.message, activeId) : false;
            const quote = quotedData(row.message, programme, displayLanguages);
            return (
              <li key={`${row.level}-${index}`}>
                <button
                  type="button"
                  className={clsx("check", "pressable", row.level, current && "is-current")}
                  onClick={() => onOpenMessage(row.message)}
                >
                  <span className="check-level">{row.level === "error" ? "Error" : "Warning"}</span>
                  {quote ? <span className="check-quote">{quote}</span> : null}
                  <span>{row.message}</span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
