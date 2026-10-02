import type { Person, Programme, RecordKind, StoredRecord } from "./types";
import { displayOrder, personName, sessionLabel, textOf } from "./text";

const KINDS: { id: RecordKind; label: string; create: string }[] = [
  { id: "conference", label: "Conference", create: "conference" },
  { id: "tracks", label: "Tracks", create: "track" },
  { id: "rooms", label: "Rooms", create: "room" },
  { id: "sessions", label: "Sessions", create: "session" },
  { id: "contributions", label: "Talks", create: "talk" },
  { id: "people", label: "People", create: "person" },
  { id: "organizations", label: "Organizations", create: "organization" },
  { id: "resources", label: "Resources", create: "resource" },
  { id: "changes", label: "Changes", create: "change" },
];

type Props = {
  programme: Programme;
  kind: RecordKind;
  selectedId: string | null;
  displayLang: string;
  onKind: (kind: RecordKind) => void;
  onSelect: (id: string) => void;
  onCreate: () => void;
};

function labelFor(kind: RecordKind, record: StoredRecord, programme: Programme, languages: string[]): string {
  if (kind === "people") {
    return personName(record as Person) || record.id;
  }
  if (kind === "sessions") {
    return sessionLabel(record as unknown as Programme["sessions"][number], programme, languages);
  }
  if (kind === "contributions") {
    return textOf(record.title as Programme["contributions"][number]["title"], languages) || record.id;
  }
  if (kind === "organizations") {
    return textOf(record.name as Programme["organizations"][number]["name"], languages) || record.id;
  }
  if (kind === "tracks") {
    return textOf(record.short as Programme["tracks"][number]["short"], languages) || record.id;
  }
  if (kind === "rooms") {
    return textOf(record.label as Programme["rooms"][number]["label"], languages) || record.id;
  }
  if (kind === "changes") {
    return textOf(record.text as Programme["changes"][number]["text"], languages) || record.id;
  }
  if (kind === "resources") {
    return `${String(record.kind || "resource")} · ${record.id}`;
  }
  return record.id;
}

export function RecordsColumn({ programme, kind, selectedId, displayLang, onKind, onSelect, onCreate }: Props) {
  const languages = displayOrder(programme.conference.languages ?? [], displayLang);
  const records: StoredRecord[] =
    kind === "conference" ? [programme.conference as unknown as StoredRecord] : (programme[kind] as StoredRecord[]);

  return (
    <section className="timetable" id="records-column" aria-label="Records">
      <div className="days" role="tablist" aria-label="Record type">
        {KINDS.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={item.id === kind}
            className={item.id === kind ? "day is-selected pressable" : "day pressable"}
            onClick={() => onKind(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>
      {kind === "conference" ? null : (
        <button type="button" className="save pressable" onClick={onCreate}>
          New {KINDS.find((item) => item.id === kind)?.create || "record"}
        </button>
      )}
      <ul className="record-list">
        {records.map((record) => (
          <li key={record.id}>
            <button
              type="button"
              className={record.id === selectedId ? "talk is-selected" : "talk"}
              onClick={() => onSelect(record.id)}
            >
              <span className="talk-title">{labelFor(kind, record, programme, languages)}</span>
              <span className="talk-meta">{record.id}</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function blankRecord(kind: RecordKind, programme: Programme): Record<string, unknown> {
  const bilingual = (text: string) => ({ ru: text, en: text });
  if (kind === "tracks") {
    return { short: bilingual("New"), full: bilingual("New track"), color: "slate" };
  }
  if (kind === "rooms") {
    return { label: bilingual("New room") };
  }
  if (kind === "sessions") {
    return {
      date: programme.conference.date_start || "2026-09-21",
      start: "09:00",
      end: "10:00",
      type: "section",
      title: bilingual("New session"),
    };
  }
  if (kind === "people") {
    return { family: "New", given: "Person" };
  }
  if (kind === "organizations") {
    return { name: "New organization" };
  }
  if (kind === "resources") {
    return {
      contribution_id: programme.contributions[0]?.id ?? "",
      kind: "slides",
      url: "https://example.org/resource",
    };
  }
  if (kind === "changes") {
    return { at: programme.conference.date_start || "2026-09-21", text: bilingual("New change") };
  }
  if (kind === "contributions") {
    return {
      format: "oral",
      title: "New talk",
      authors: [{ person_id: programme.people[0]?.id ?? "", affiliation_ids: [], presenting: true }],
      status: "ok",
    };
  }
  return {};
}
