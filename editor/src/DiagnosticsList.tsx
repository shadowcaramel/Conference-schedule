import clsx from "clsx";
import type { Diagnostics } from "./types";
import { mentionsId } from "./text";

type Props = {
  diagnostics: Diagnostics;
  activeId: string | null;
  onOpenMessage: (message: string) => void;
};

export function DiagnosticsList({ diagnostics, activeId, onOpenMessage }: Props) {
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
            return (
              <li key={`${row.level}-${index}`}>
                <button
                  type="button"
                  className={clsx("check", "pressable", row.level, current && "is-current")}
                  onClick={() => onOpenMessage(row.message)}
                >
                  <span className="check-level">{row.level === "error" ? "Error" : "Warning"}</span>
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
