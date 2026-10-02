import { useMemo, useState } from "react";
import type { Programme, RecordKind } from "./types";
import { displayOrder, personName, textOf } from "./text";

type Hit = {
  kind: "contributions" | "people" | "organizations";
  id: string;
  label: string;
  meta: string;
};

type Props = {
  programme: Programme;
  displayLang: string;
  onOpen: (kind: RecordKind, id: string) => void;
};

export function ProgrammeSearch({ programme, displayLang, onOpen }: Props) {
  const languages = displayOrder(programme.conference.languages ?? [], displayLang);
  const [query, setQuery] = useState("");
  const hits = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) {
      return [];
    }
    const found: Hit[] = [];
    for (const talk of programme.contributions) {
      const label = textOf(talk.title, languages) || talk.id;
      const blob = `${label} ${talk.number ?? ""} ${talk.id}`.toLowerCase();
      if (blob.includes(needle)) {
        found.push({ kind: "contributions", id: talk.id, label, meta: "Talk" });
      }
    }
    for (const person of programme.people) {
      const label = personName(person) || person.id;
      const blob = `${label} ${person.email ?? ""} ${person.id}`.toLowerCase();
      if (blob.includes(needle)) {
        found.push({ kind: "people", id: person.id, label, meta: "Person" });
      }
    }
    for (const org of programme.organizations) {
      const label = textOf(org.name, languages) || org.id;
      const blob = `${label} ${org.id}`.toLowerCase();
      if (blob.includes(needle)) {
        found.push({ kind: "organizations", id: org.id, label, meta: "Organization" });
      }
    }
    return found.slice(0, 12);
  }, [query, programme, languages]);

  return (
    <div className="search">
      <label className="field" htmlFor="programme-search">
        <span className="sr-only">Search talks, people, and organizations</span>
        <input
          id="programme-search"
          value={query}
          placeholder="Search talks, people, organizations"
          autoComplete="off"
          onChange={(event) => setQuery(event.target.value)}
        />
      </label>
      {hits.length > 0 ? (
        <ul className="search-hits" role="listbox" aria-label="Search results">
          {hits.map((hit) => (
            <li key={`${hit.kind}-${hit.id}`}>
              <button
                type="button"
                role="option"
                onClick={() => {
                  onOpen(hit.kind, hit.id);
                  setQuery("");
                }}
              >
                <span>{hit.label}</span>
                <span className="talk-meta">
                  {hit.meta} · {hit.id}
                </span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
