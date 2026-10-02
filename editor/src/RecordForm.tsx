import { useEffect, useMemo, useState, type FormEvent } from "react";
import { toast } from "sonner";
import { saveRecord, validateRecord } from "./api";
import { bilingualPayload, languageMap } from "./bilingual";
import { DeleteControl } from "./DeleteControl";
import { NamePicker, type NameOption } from "./NamePicker";
import type { Diagnostics, ForRecord, Programme, RecordKind, SaveResult, StoredRecord } from "./types";
import { languageLabel, displayOrder, textOf } from "./text";

type Props = {
  kind: Exclude<RecordKind, "contributions">;
  record: StoredRecord;
  programme: Programme;
  displayLang: string;
  onSaved: (result: SaveResult) => void;
  onDraftDiagnostics: (diagnostics: Diagnostics) => void;
  onCreatePerson: (draft: { family: string; given: string }) => Promise<string>;
  onDeleted: () => void;
};

const FORM_TITLE: Record<Exclude<RecordKind, "contributions">, string> = {
  conference: "Conference",
  tracks: "Track",
  rooms: "Room",
  sessions: "Session",
  people: "Person",
  organizations: "Organization",
  resources: "Resource",
  changes: "Change",
};

const COLORS = ["blue", "green", "orange", "red", "purple", "teal", "pink", "slate"];
const SESSION_TYPES = [
  "plenary",
  "jubilee",
  "sponsor",
  "section",
  "break",
  "lunch",
  "registration",
  "opening",
  "closing",
  "poster",
  "social",
];
const RESOURCE_KINDS = ["slides", "video", "abstract", "photo", "poster"];
const DURATION_KEYS = ["plenary", "jubilee", "sponsor", "section"];

const EMPTY_RECORD: ForRecord = { id: "", errors: [], warnings: [] };

function cloneRecord(record: StoredRecord): StoredRecord {
  return JSON.parse(JSON.stringify(record)) as StoredRecord;
}

function asText(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function BilingualFields({
  label,
  languages,
  value,
  onChange,
  rows = 2,
}: {
  label: string;
  languages: string[];
  value: unknown;
  onChange: (next: Record<string, string> | undefined) => void;
  rows?: number;
}) {
  const map = languageMap(value, languages, true);
  return (
    <>
      {languages.map((lang) => (
        <label className="field" key={`${label}-${lang}`}>
          <span>
            {label} · {languageLabel(lang)}
          </span>
          <textarea
            rows={rows}
            value={map[lang] ?? ""}
            onChange={(event) => {
              const next = { ...map, [lang]: event.target.value };
              onChange(bilingualPayload(next, languages));
            }}
          />
        </label>
      ))}
    </>
  );
}

export function RecordForm({
  kind,
  record,
  programme,
  displayLang,
  onSaved,
  onDraftDiagnostics,
  onCreatePerson,
  onDeleted,
}: Props) {
  const languages = programme.conference.languages ?? [];
  const shown = useMemo(() => displayOrder(languages, displayLang), [languages, displayLang]);
  const [draft, setDraft] = useState<StoredRecord>(() => cloneRecord(record));
  const [nameWasString, setNameWasString] = useState(typeof record.name === "string");
  const [checks, setChecks] = useState<ForRecord>(EMPTY_RECORD);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setDraft(cloneRecord(record));
    setNameWasString(typeof record.name === "string");
  }, [record]);

  const serialized = JSON.stringify(draft);

  useEffect(() => {
    let cancelled = false;
    const handle = window.setTimeout(() => {
      validateRecord(kind, JSON.parse(serialized) as StoredRecord)
        .then((result) => {
          if (cancelled) {
            return;
          }
          setChecks(result.for_record ?? { ...EMPTY_RECORD, id: record.id });
          onDraftDiagnostics(result.diagnostics);
        })
        .catch((error: unknown) => {
          if (!cancelled) {
            toast.error(error instanceof Error ? error.message : "Validation failed");
          }
        });
    }, 300);
    return () => {
      cancelled = true;
      window.clearTimeout(handle);
    };
  }, [serialized, kind, record.id, onDraftDiagnostics]);

  const people = useMemo<NameOption[]>(
    () =>
      programme.people.map((person) => ({
        id: person.id,
        label: [person.family, person.given, person.patronymic].filter(Boolean).join(" ") || person.id,
      })),
    [programme.people],
  );
  const tracks = useMemo<NameOption[]>(
    () => programme.tracks.map((track) => ({ id: track.id, label: textOf(track.short, shown) || track.id })),
    [programme.tracks, shown],
  );
  const rooms = useMemo<NameOption[]>(
    () => programme.rooms.map((room) => ({ id: room.id, label: textOf(room.label, shown) || room.id })),
    [programme.rooms, shown],
  );
  const talks = useMemo<NameOption[]>(
    () =>
      programme.contributions.map((talk) => ({
        id: talk.id,
        label: textOf(talk.title, shown) || talk.id,
      })),
    [programme.contributions, shown],
  );

  function setField(key: string, value: unknown) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  function prepared(): StoredRecord {
    const next = cloneRecord(draft);
    if (kind === "organizations" && nameWasString && next.name && typeof next.name === "object") {
      const map = languageMap(next.name, languages, true);
      const values = languages.map((lang) => map[lang] ?? "");
      if (values.every((value) => value === values[0])) {
        next.name = values[0] ?? "";
      }
    }
    if (kind === "conference" && Array.isArray(next.languages)) {
      next.languages = (next.languages as string[]).map((item) => item.trim()).filter(Boolean);
    }
    if (kind === "rooms" && Array.isArray(next.aliases)) {
      next.aliases = (next.aliases as string[]).map((item) => item.trim()).filter(Boolean);
    }
    return next;
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      const result = await saveRecord(kind, prepared());
      toast.success("Saved");
      onSaved(result);
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  const messages = [
    ...checks.errors.map((message) => ({ level: "error" as const, message })),
    ...checks.warnings.map((message) => ({ level: "warning" as const, message })),
  ];
  const chairs = Array.isArray(draft.chairs) ? (draft.chairs as { person_id?: string; label?: unknown }[]) : [];
  const durations =
    draft.defaults && typeof draft.defaults === "object"
      ? ((draft.defaults as { duration_min?: Record<string, number> }).duration_min ?? {})
      : {};
  const sessionTypes =
    draft.session_types && typeof draft.session_types === "object"
      ? (draft.session_types as Record<string, unknown>)
      : {};
  const aliases = Array.isArray(draft.aliases) ? (draft.aliases as string[]) : [];
  const languageList = Array.isArray(draft.languages) ? (draft.languages as string[]) : languages;

  return (
    <form className="detail form" id="record-form" onSubmit={onSubmit} aria-label={`${kind} form`}>
      <header className="detail-head">
        <h2>{FORM_TITLE[kind]}</h2>
      </header>
      <div className="readonly">
        <span>ID</span>
        <strong>{draft.id}</strong>
      </div>
      <div className="record-checks" aria-live="polite">
        {messages.length === 0 ? (
          <p className="quiet">No issues on this record.</p>
        ) : (
          messages.map((item, index) => (
            <p key={`${item.level}-${index}`} className={item.level === "error" ? "issue error" : "issue warning"}>
              <span>{item.level === "error" ? "Error" : "Warning"}</span>
              {item.message}
            </p>
          ))
        )}
      </div>

      {kind === "people" ? (
        <>
          <label className="field">
            <span>Family name</span>
            <input value={asText(draft.family)} onChange={(event) => setField("family", event.target.value)} />
          </label>
          <label className="field">
            <span>Given name</span>
            <input value={asText(draft.given)} onChange={(event) => setField("given", event.target.value)} />
          </label>
          <label className="field">
            <span>Patronymic</span>
            <input value={asText(draft.patronymic)} onChange={(event) => setField("patronymic", event.target.value)} />
          </label>
          <label className="field">
            <span>Email</span>
            <input value={asText(draft.email)} onChange={(event) => setField("email", event.target.value)} />
          </label>
        </>
      ) : null}

      {kind === "organizations" ? (
        <>
          <BilingualFields label="Name" languages={languages} value={draft.name} onChange={(next) => setField("name", next)} />
          <label className="field">
            <span>URL</span>
            <input value={asText(draft.url)} onChange={(event) => setField("url", event.target.value)} />
          </label>
          <label className="field">
            <span>Logo</span>
            <input value={asText(draft.logo)} onChange={(event) => setField("logo", event.target.value)} />
          </label>
        </>
      ) : null}

      {kind === "tracks" ? (
        <>
          <BilingualFields label="Short name" languages={languages} value={draft.short} onChange={(next) => setField("short", next)} rows={1} />
          <BilingualFields label="Full name" languages={languages} value={draft.full} onChange={(next) => setField("full", next)} />
          <label className="field">
            <span>Colour</span>
            <select value={asText(draft.color) || "slate"} onChange={(event) => setField("color", event.target.value)}>
              {COLORS.map((color) => (
                <option key={color} value={color}>
                  {color}
                </option>
              ))}
            </select>
          </label>
        </>
      ) : null}

      {kind === "rooms" ? (
        <>
          <BilingualFields label="Label" languages={languages} value={draft.label} onChange={(next) => setField("label", next)} rows={1} />
          <label className="field">
            <span>Aliases, one per line</span>
            <textarea
              rows={3}
              value={aliases.join("\n")}
              onChange={(event) => setField("aliases", event.target.value.split("\n"))}
            />
          </label>
        </>
      ) : null}

      {kind === "resources" ? (
        <>
          <NamePicker
            label="Contribution"
            options={talks}
            value={asText(draft.contribution_id)}
            onChange={(id) => setField("contribution_id", id)}
          />
          <label className="field">
            <span>Kind</span>
            <select value={asText(draft.kind) || "slides"} onChange={(event) => setField("kind", event.target.value)}>
              {RESOURCE_KINDS.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>URL</span>
            <input value={asText(draft.url)} onChange={(event) => setField("url", event.target.value)} />
          </label>
          <label className="field">
            <span>Language code</span>
            <input value={asText(draft.lang)} onChange={(event) => setField("lang", event.target.value)} />
          </label>
        </>
      ) : null}

      {kind === "changes" ? (
        <>
          <label className="field">
            <span>When</span>
            <input value={asText(draft.at)} onChange={(event) => setField("at", event.target.value)} placeholder="YYYY-MM-DD" />
          </label>
          <BilingualFields label="Text" languages={languages} value={draft.text} onChange={(next) => setField("text", next)} />
        </>
      ) : null}

      {kind === "sessions" ? (
        <>
          <div className="split">
            <label className="field">
              <span>Date</span>
              <input value={asText(draft.date)} onChange={(event) => setField("date", event.target.value)} />
            </label>
            <label className="field">
              <span>Type</span>
              <select value={asText(draft.type)} onChange={(event) => setField("type", event.target.value)}>
                {SESSION_TYPES.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="split">
            <label className="field">
              <span>Start</span>
              <input value={asText(draft.start)} onChange={(event) => setField("start", event.target.value)} placeholder="HH:MM" />
            </label>
            <label className="field">
              <span>End</span>
              <input value={asText(draft.end)} onChange={(event) => setField("end", event.target.value)} placeholder="HH:MM" />
            </label>
          </div>
          <BilingualFields label="Title" languages={languages} value={draft.title} onChange={(next) => setField("title", next)} rows={1} />
          <NamePicker label="Track" options={tracks} value={asText(draft.track_id)} onChange={(id) => setField("track_id", id)} />
          <NamePicker label="Room" options={rooms} value={asText(draft.room_id)} onChange={(id) => setField("room_id", id)} />
          <div className="authors">
            {chairs.map((chair, index) => (
              <fieldset className="author" key={`${draft.id}-chair-${index}`}>
                <legend>Chair {index + 1}</legend>
                <NamePicker
                  label="Person"
                  options={people}
                  value={chair.person_id ?? ""}
                  onCreatePerson={onCreatePerson}
                  onChange={(id) => {
                    const next = chairs.map((item, itemIndex) => (itemIndex === index ? { ...item, person_id: id } : item));
                    setField("chairs", next);
                  }}
                />
                <BilingualFields
                  label="Published label"
                  languages={languages}
                  value={chair.label}
                  rows={1}
                  onChange={(next) => {
                    const updated = chairs.map((item, itemIndex) => (itemIndex === index ? { ...item, label: next } : item));
                    setField("chairs", updated);
                  }}
                />
                <button
                  type="button"
                  className="text-button pressable"
                  onClick={() => setField("chairs", chairs.filter((_, itemIndex) => itemIndex !== index))}
                >
                  Remove chair
                </button>
              </fieldset>
            ))}
            <button
              type="button"
              className="text-button pressable"
              onClick={() => setField("chairs", [...chairs, { person_id: "" }])}
            >
              Add chair
            </button>
          </div>
          <BilingualFields label="Note" languages={languages} value={draft.note} onChange={(next) => setField("note", next)} />
          <div className="readonly">
            <span>Talks</span>
            <strong>{Array.isArray(draft.contribution_ids) ? draft.contribution_ids.length : 0}</strong>
          </div>
        </>
      ) : null}

      {kind === "conference" ? (
        <>
          <BilingualFields label="Title" languages={languages} value={draft.title} onChange={(next) => setField("title", next)} rows={1} />
          <BilingualFields
            label="Short title"
            languages={languages}
            value={draft.short_title}
            onChange={(next) => setField("short_title", next)}
            rows={1}
          />
          <BilingualFields label="City" languages={languages} value={draft.city} onChange={(next) => setField("city", next)} rows={1} />
          <BilingualFields label="Venue" languages={languages} value={draft.venue} onChange={(next) => setField("venue", next)} rows={1} />
          <BilingualFields label="Footnote" languages={languages} value={draft.footnote} onChange={(next) => setField("footnote", next)} />
          <div className="split">
            <label className="field">
              <span>First day</span>
              <input value={asText(draft.date_start)} onChange={(event) => setField("date_start", event.target.value)} />
            </label>
            <label className="field">
              <span>Last day</span>
              <input value={asText(draft.date_end)} onChange={(event) => setField("date_end", event.target.value)} />
            </label>
          </div>
          <label className="field">
            <span>Timezone</span>
            <input value={asText(draft.timezone)} onChange={(event) => setField("timezone", event.target.value)} />
          </label>
          <label className="field">
            <span>Website</span>
            <input value={asText(draft.website)} onChange={(event) => setField("website", event.target.value)} />
          </label>
          <label className="field">
            <span>Contact</span>
            <input value={asText(draft.contact)} onChange={(event) => setField("contact", event.target.value)} />
          </label>
          <label className="field">
            <span>Languages, in form order</span>
            <input
              value={languageList.join(", ")}
              onChange={(event) =>
                setField(
                  "languages",
                  event.target.value.split(",").map((item) => item.trim()),
                )
              }
            />
          </label>
          <fieldset className="author">
            <legend>Default durations (minutes)</legend>
            {DURATION_KEYS.map((key) => (
              <label className="field" key={key}>
                <span>{key}</span>
                <input
                  inputMode="numeric"
                  value={durations[key] ?? ""}
                  onChange={(event) => {
                    const raw = event.target.value.trim();
                    const duration_min = { ...durations };
                    if (raw === "") {
                      delete duration_min[key];
                    } else {
                      duration_min[key] = Number(raw);
                    }
                    setField("defaults", { duration_min });
                  }}
                />
              </label>
            ))}
          </fieldset>
          <fieldset className="author">
            <legend>Session type labels</legend>
            {Object.keys(sessionTypes).map((key) => (
              <BilingualFields
                key={key}
                label={key}
                languages={languages}
                value={sessionTypes[key]}
                rows={1}
                onChange={(next) => setField("session_types", { ...sessionTypes, [key]: next })}
              />
            ))}
          </fieldset>
        </>
      ) : null}

      <button type="submit" className="save pressable" disabled={saving}>
        {saving ? "Saving…" : "Save"}
      </button>
      {kind === "conference" ? null : (
        <DeleteControl kind={kind} id={String(draft.id)} programme={programme} displayLang={displayLang} onDeleted={onDeleted} />
      )}
    </form>
  );
}
