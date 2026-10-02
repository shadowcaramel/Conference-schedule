import { useEffect, useMemo, useState, type FormEvent } from "react";
import { toast } from "sonner";
import { saveContribution, validateContribution } from "./api";
import { NamePicker, type NameOption } from "./NamePicker";
import type { Author, Contribution, Diagnostics, ForRecord, Programme, SaveResult } from "./types";
import { languageLabel, sessionLabel, textOf } from "./text";

type Props = {
  programme: Programme;
  contribution: Contribution;
  onBack: () => void;
  onSaved: (result: SaveResult) => void;
  onDraftDiagnostics: (diagnostics: Diagnostics) => void;
};

const EMPTY_RECORD: ForRecord = { id: "", errors: [], warnings: [] };

function languageMap(value: Contribution["title"] | undefined, languages: string[], copyString: boolean): Record<string, string> {
  if (typeof value === "string") {
    return Object.fromEntries(languages.map((lang) => [lang, copyString ? value : ""]));
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(languages.map((lang) => [lang, value[lang] ?? ""]));
  }
  return Object.fromEntries(languages.map((lang) => [lang, ""]));
}

function materialize(
  draft: Contribution,
  titleByLang: Record<string, string>,
  noteByLang: Record<string, string>,
  languages: string[],
  titleWasString: boolean,
): Contribution {
  const next: Contribution = {
    ...draft,
    authors: draft.authors.map((author) => ({
      person_id: author.person_id,
      affiliation_ids: author.affiliation_ids.filter((id) => id),
      presenting: Boolean(author.presenting),
    })),
  };
  const titleValues = languages.map((lang) => titleByLang[lang] ?? "");
  const unchangedString = titleWasString && titleValues.every((value) => value === titleValues[0]);
  if (unchangedString) {
    next.title = titleValues[0] ?? "";
  } else {
    const title: Record<string, string> = {};
    for (const lang of languages) {
      title[lang] = titleByLang[lang] ?? "";
    }
    if (!("ru" in title)) {
      title.ru = "";
    }
    if (!("en" in title)) {
      title.en = "";
    }
    next.title = title;
  }
  const note: Record<string, string> = {};
  let anyNote = false;
  for (const lang of languages) {
    note[lang] = noteByLang[lang] ?? "";
    if (note[lang].trim()) {
      anyNote = true;
    }
  }
  if (anyNote) {
    if (!("ru" in note)) {
      note.ru = "";
    }
    if (!("en" in note)) {
      note.en = "";
    }
    next.note = note;
  } else {
    delete next.note;
  }
  if (!next.duration_min) {
    delete next.duration_min;
  }
  for (const key of ["track_id", "number", "start", "topic_id", "sponsor_id", "board"] as const) {
    if (!next[key]) {
      delete next[key];
    }
  }
  return next;
}

export function ContributionForm({ programme, contribution, onBack, onSaved, onDraftDiagnostics }: Props) {
  const languages = programme.conference.languages ?? [];
  const [draft, setDraft] = useState<Contribution>(contribution);
  const [titleWasString, setTitleWasString] = useState(typeof contribution.title === "string");
  const [titleByLang, setTitleByLang] = useState(() => languageMap(contribution.title, languages, true));
  const [noteByLang, setNoteByLang] = useState(() => languageMap(contribution.note, languages, false));
  const [recordChecks, setRecordChecks] = useState<ForRecord>(EMPTY_RECORD);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setDraft(contribution);
    setTitleWasString(typeof contribution.title === "string");
    setTitleByLang(languageMap(contribution.title, languages, true));
    setNoteByLang(languageMap(contribution.note, languages, false));
  }, [contribution, languages]);

  const payload = useMemo(
    () => materialize(draft, titleByLang, noteByLang, languages, titleWasString),
    [draft, titleByLang, noteByLang, languages, titleWasString],
  );
  const serialized = JSON.stringify(payload);

  useEffect(() => {
    let cancelled = false;
    const handle = window.setTimeout(() => {
      validateContribution(JSON.parse(serialized) as Contribution)
        .then((result) => {
          if (cancelled) {
            return;
          }
          setRecordChecks(result.for_record ?? { ...EMPTY_RECORD, id: contribution.id });
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
  }, [serialized, contribution.id, onDraftDiagnostics]);

  const people = useMemo<NameOption[]>(
    () =>
      programme.people.map((person) => ({
        id: person.id,
        label: [person.family, person.given, person.patronymic].filter(Boolean).join(" ") || person.id,
      })),
    [programme.people],
  );
  const organizations = useMemo<NameOption[]>(
    () =>
      programme.organizations.map((org) => ({
        id: org.id,
        label: textOf(org.name, languages) || org.id,
      })),
    [programme.organizations, languages],
  );
  const tracks = useMemo<NameOption[]>(
    () =>
      programme.tracks.map((track) => ({
        id: track.id,
        label: textOf(track.short, languages) || track.id,
      })),
    [programme.tracks, languages],
  );

  const session = programme.sessions.find((item) => item.id === draft.session_id);
  const room = programme.rooms.find((item) => item.id === session?.room_id);
  const slot = programme.placement.contributions[draft.id];

  function updateAuthor(index: number, author: Author) {
    setDraft((current) => ({
      ...current,
      authors: current.authors.map((item, itemIndex) => (itemIndex === index ? author : item)),
    }));
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      const result = await saveContribution(payload);
      toast.success("Saved");
      onSaved(result);
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  const messages = [...recordChecks.errors.map((message) => ({ level: "error" as const, message })), ...recordChecks.warnings.map((message) => ({ level: "warning" as const, message }))];

  return (
    <form className="detail form" id="contribution-form" onSubmit={onSubmit} aria-label="Contribution">
      <header className="detail-head">
        <button type="button" className="text-button pressable" onClick={onBack}>
          Back to talks
        </button>
        <h2>Contribution</h2>
      </header>

      <div className="readonly">
        <span>ID</span>
        <strong>{draft.id}</strong>
      </div>
      <div className="readonly">
        <span>Session</span>
        <strong>
          {session
            ? `${sessionLabel(session, programme)} · ${textOf(room?.label, languages) || "No room"}`
            : "Not scheduled"}
        </strong>
      </div>
      <div className="readonly">
        <span>Computed time</span>
        <strong>{slot ? `${slot.start}–${slot.end}` : "Not placed"}</strong>
      </div>
      {draft.order ? (
        <div className="readonly">
          <span>Order in session</span>
          <strong>{draft.order}</strong>
        </div>
      ) : null}

      <div className="record-checks" aria-live="polite">
        {messages.length === 0 ? (
          <p className="quiet">No issues on this contribution.</p>
        ) : (
          messages.map((item, index) => (
            <p key={`${item.level}-${index}`} className={item.level === "error" ? "issue error" : "issue warning"}>
              <span>{item.level === "error" ? "Error" : "Warning"}</span>
              {item.message}
            </p>
          ))
        )}
      </div>

      {languages.map((lang) => (
        <label className="field" key={`title-${lang}`}>
          <span>Title · {languageLabel(lang)}</span>
          <textarea
            rows={3}
            value={titleByLang[lang] ?? ""}
            onChange={(event) => setTitleByLang((current) => ({ ...current, [lang]: event.target.value }))}
          />
        </label>
      ))}

      <div className="split">
        <label className="field">
          <span>Format</span>
          <select
            value={draft.format}
            onChange={(event) => setDraft((current) => ({ ...current, format: event.target.value }))}
          >
            <option value="oral">Oral</option>
            <option value="poster">Poster</option>
          </select>
        </label>
        <label className="field">
          <span>Status</span>
          <select
            value={draft.status}
            onChange={(event) => setDraft((current) => ({ ...current, status: event.target.value }))}
          >
            <option value="ok">Ok</option>
            <option value="cancelled">Cancelled</option>
            <option value="moved">Moved</option>
          </select>
        </label>
      </div>

      <NamePicker
        label="Track"
        options={tracks}
        value={draft.track_id ?? ""}
        onChange={(id) => setDraft((current) => ({ ...current, track_id: id }))}
      />
      <NamePicker
        label="Topic"
        options={tracks}
        value={draft.topic_id ?? ""}
        onChange={(id) => setDraft((current) => ({ ...current, topic_id: id }))}
      />

      <div className="split">
        <label className="field">
          <span>Number</span>
          <input
            value={draft.number ?? ""}
            onChange={(event) => setDraft((current) => ({ ...current, number: event.target.value }))}
          />
        </label>
        <label className="field">
          <span>Duration (minutes)</span>
          <input
            inputMode="numeric"
            value={draft.duration_min ?? ""}
            onChange={(event) => {
              const raw = event.target.value.trim();
              setDraft((current) => ({
                ...current,
                duration_min: raw === "" ? undefined : Number(raw),
              }));
            }}
          />
        </label>
      </div>
      <div className="split">
        <label className="field">
          <span>Start pin</span>
          <input
            value={draft.start ?? ""}
            placeholder="HH:MM"
            onChange={(event) => setDraft((current) => ({ ...current, start: event.target.value }))}
          />
        </label>
        <label className="field">
          <span>Poster board</span>
          <input
            value={draft.board ?? ""}
            onChange={(event) => setDraft((current) => ({ ...current, board: event.target.value }))}
          />
        </label>
      </div>

      <div className="authors">
        {draft.authors.map((author, index) => (
          <fieldset className="author" key={`${draft.id}-author-${index}`}>
            <legend>Author {index + 1}</legend>
            <NamePicker
              label="Person"
              options={people}
              value={author.person_id}
              onChange={(id) => updateAuthor(index, { ...author, person_id: id })}
            />
            {author.affiliation_ids.map((orgId, affIndex) => (
              <NamePicker
                key={`${index}-aff-${affIndex}`}
                label={`Affiliation ${affIndex + 1}`}
                options={organizations}
                value={orgId}
                onChange={(id) => {
                  const affiliation_ids = author.affiliation_ids.map((item, itemIndex) =>
                    itemIndex === affIndex ? id : item,
                  );
                  updateAuthor(index, { ...author, affiliation_ids });
                }}
              />
            ))}
            <div className="row-actions">
              <button
                type="button"
                className="text-button pressable"
                onClick={() =>
                  updateAuthor(index, { ...author, affiliation_ids: [...author.affiliation_ids, ""] })
                }
              >
                Add affiliation
              </button>
              <label className="checkline">
                <input
                  type="checkbox"
                  checked={author.presenting}
                  onChange={(event) => updateAuthor(index, { ...author, presenting: event.target.checked })}
                />
                Presenting
              </label>
              <button
                type="button"
                className="text-button pressable"
                onClick={() =>
                  setDraft((current) => ({
                    ...current,
                    authors: current.authors.filter((_, itemIndex) => itemIndex !== index),
                  }))
                }
              >
                Remove author
              </button>
            </div>
          </fieldset>
        ))}
        <button
          type="button"
          className="text-button pressable"
          onClick={() =>
            setDraft((current) => ({
              ...current,
              authors: [...current.authors, { person_id: "", affiliation_ids: [], presenting: false }],
            }))
          }
        >
          Add author
        </button>
      </div>

      <NamePicker
        label="Sponsor"
        options={organizations}
        value={draft.sponsor_id ?? ""}
        onChange={(id) => setDraft((current) => ({ ...current, sponsor_id: id }))}
      />

      {languages.map((lang) => (
        <label className="field" key={`note-${lang}`}>
          <span>Note · {languageLabel(lang)}</span>
          <textarea
            rows={2}
            value={noteByLang[lang] ?? ""}
            onChange={(event) => setNoteByLang((current) => ({ ...current, [lang]: event.target.value }))}
          />
        </label>
      ))}

      <button type="submit" className="save pressable" disabled={saving}>
        {saving ? "Saving…" : "Save contribution"}
      </button>
    </form>
  );
}
