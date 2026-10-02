import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { createRecord, loadProgramme } from "./api";
import { ContributionForm } from "./ContributionForm";
import { DiagnosticsList } from "./DiagnosticsList";
import { DuplicatesBanner } from "./DuplicatesBanner";
import { LanguageSwitch } from "./LanguageSwitch";
import { ProgrammeSearch } from "./ProgrammeSearch";
import { RecordForm } from "./RecordForm";
import { blankRecord, RecordsColumn } from "./RecordsColumn";
import { SessionDetail } from "./SessionDetail";
import { Timetable } from "./Timetable";
import type { Contribution, Diagnostics, Programme, RecordKind, SaveResult, StoredRecord } from "./types";
import { activeLanguage, displayOrder, mentionsId, readStoredLanguage, storeLanguage, textOf } from "./text";

export function App() {
  const [programme, setProgramme] = useState<Programme | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [day, setDay] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftDiagnostics, setDraftDiagnostics] = useState<Diagnostics | null>(null);
  const [storedLang, setStoredLang] = useState<string | null>(() => readStoredLanguage());
  const [mode, setMode] = useState<"timetable" | "records">("timetable");
  const [kind, setKind] = useState<RecordKind>("people");
  const [recordId, setRecordId] = useState<string | null>(null);

  const reload = useCallback(() => {
    return loadProgramme()
      .then((data) => {
        setProgramme(data);
        return data;
      })
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Could not load the programme");
        return null;
      });
  }, []);

  useEffect(() => {
    reload().then((data) => {
      if (!data) {
        return;
      }
      const first = [...data.sessions].sort((a, b) => a.date.localeCompare(b.date))[0];
      setDay(first?.date ?? null);
    });
  }, [reload]);

  const onDraftDiagnostics = useCallback((diagnostics: Diagnostics) => {
    setDraftDiagnostics(diagnostics);
  }, []);

  const days = useMemo(() => {
    if (!programme) {
      return [];
    }
    return [...new Set(programme.sessions.map((session) => session.date))].sort();
  }, [programme]);

  const languages = programme?.conference.languages ?? [];
  const displayLang = activeLanguage(languages, storedLang);

  useEffect(() => {
    if (programme) {
      document.documentElement.lang = displayLang;
    }
  }, [programme, displayLang]);

  const createPerson = useCallback(async (draft: { family: string; given: string }) => {
    const result = await createRecord("people", draft);
    setProgramme((current) => {
      if (!current) {
        return current;
      }
      const person = result.record as Programme["people"][number];
      const people = [...current.people.filter((item) => item.id !== person.id), person].sort((a, b) =>
        a.id.localeCompare(b.id),
      );
      return { ...current, people, placement: result.placement, diagnostics: result.diagnostics };
    });
    toast.success("Person created");
    return result.record.id;
  }, []);

  if (error) {
    return (
      <main className="boot">
        <h1>Programme editor</h1>
        <p>{error}</p>
      </main>
    );
  }
  if (!programme) {
    return (
      <main className="boot">
        <h1>Programme editor</h1>
        <p>Loading the programme…</p>
      </main>
    );
  }

  const activeDay = day ?? days[0] ?? "";
  const shown = displayOrder(languages, displayLang);
  const session = programme.sessions.find((item) => item.id === sessionId) ?? null;
  const contribution = programme.contributions.find((item) => item.id === editingId) ?? null;
  const recordContribution = programme.contributions.find((item) => item.id === recordId) ?? null;
  const entity =
    kind === "conference"
      ? (programme.conference as unknown as StoredRecord)
      : ((programme[kind] as StoredRecord[]).find((item) => item.id === recordId) ?? null);
  const diagnostics =
    (editingId || (mode === "records" && recordId)) && draftDiagnostics ? draftDiagnostics : programme.diagnostics;

  function openSession(id: string) {
    setMode("timetable");
    setSessionId(id);
    setEditingId(null);
    setDraftDiagnostics(null);
  }

  function openContribution(id: string) {
    const talk = programme?.contributions.find((item) => item.id === id);
    if (!talk) {
      return;
    }
    setMode("timetable");
    if (talk.session_id) {
      const host = programme?.sessions.find((item) => item.id === talk.session_id);
      if (host) {
        setDay(host.date);
        setSessionId(host.id);
      }
    }
    setEditingId(id);
    setDraftDiagnostics(null);
  }

  function openRecord(nextKind: RecordKind, id: string) {
    if (nextKind === "contributions") {
      openContribution(id);
      return;
    }
    if (nextKind === "sessions") {
      openSession(id);
      return;
    }
    setMode("records");
    setKind(nextKind);
    setRecordId(id);
    setEditingId(null);
    setDraftDiagnostics(null);
  }

  function onSaved(result: SaveResult) {
    setProgramme((current) => {
      if (!current) {
        return current;
      }
      return {
        ...current,
        contributions: current.contributions.map((item) =>
          item.id === result.record.id ? (result.record as unknown as Contribution) : item,
        ),
        placement: result.placement,
        diagnostics: result.diagnostics,
      };
    });
    setDraftDiagnostics(result.diagnostics);
  }

  function onEntitySaved(result: SaveResult) {
    setProgramme((current) => {
      if (!current) {
        return current;
      }
      if (kind === "conference") {
        return {
          ...current,
          conference: result.record as unknown as Programme["conference"],
          placement: result.placement,
          diagnostics: result.diagnostics,
        };
      }
      const list = current[kind] as StoredRecord[];
      const next = list.some((item) => item.id === result.record.id)
        ? list.map((item) => (item.id === result.record.id ? result.record : item))
        : [...list, result.record];
      return { ...current, [kind]: next, placement: result.placement, diagnostics: result.diagnostics };
    });
    setDraftDiagnostics(result.diagnostics);
  }

  function onOpenMessage(message: string) {
    if (!programme) {
      return;
    }
    const contributionHit = programme.contributions
      .map((item) => item.id)
      .filter((id) => mentionsId(message, id))
      .sort((a, b) => b.length - a.length)[0];
    if (contributionHit) {
      openContribution(contributionHit);
      return;
    }
    const sessionHit = programme.sessions
      .map((item) => item.id)
      .filter((id) => mentionsId(message, id))
      .sort((a, b) => b.length - a.length)[0];
    if (sessionHit) {
      const host = programme.sessions.find((item) => item.id === sessionHit);
      if (host) {
        setDay(host.date);
      }
      openSession(sessionHit);
      return;
    }
    const lists: { kind: RecordKind; ids: string[] }[] = [
      { kind: "people", ids: programme.people.map((item) => item.id) },
      { kind: "organizations", ids: programme.organizations.map((item) => item.id) },
      { kind: "rooms", ids: programme.rooms.map((item) => item.id) },
      { kind: "resources", ids: programme.resources.map((item) => item.id) },
      { kind: "changes", ids: programme.changes.map((item) => item.id) },
    ];
    for (const list of lists) {
      const hit = list.ids.filter((id) => mentionsId(message, id)).sort((a, b) => b.length - a.length)[0];
      if (hit) {
        openRecord(list.kind, hit);
        return;
      }
    }
    toast.message("That check is not a contribution or a session.");
  }

  async function onCreateKind() {
    if (!programme || kind === "conference") {
      return;
    }
    try {
      const result = await createRecord(kind, blankRecord(kind, programme));
      onEntitySaved(result);
      setRecordId(result.record.id);
      toast.success("Created");
    } catch (reason: unknown) {
      toast.error(reason instanceof Error ? reason.message : "Could not create a record");
    }
  }

  const formContribution = mode === "records" && kind === "contributions" ? recordContribution : contribution;

  return (
    <div className="app">
      <header className="top">
        <div>
          <p className="eyebrow">Local programme editor</p>
          <h1>{textOf(programme.conference.short_title, shown) || "Programme"}</h1>
        </div>
        <ProgrammeSearch programme={programme} displayLang={displayLang} onOpen={openRecord} />
        <div className="top-actions">
          <div className="mode-switch" role="group" aria-label="Editor view">
            <button
              type="button"
              className={mode === "timetable" ? "day is-selected pressable" : "day pressable"}
              aria-pressed={mode === "timetable"}
              onClick={() => setMode("timetable")}
            >
              Timetable
            </button>
            <button
              type="button"
              className={mode === "records" ? "day is-selected pressable" : "day pressable"}
              aria-pressed={mode === "records"}
              onClick={() => {
                setMode("records");
                if (kind === "conference") {
                  setRecordId(programme.conference.id);
                }
              }}
            >
              Records
            </button>
          </div>
          <LanguageSwitch
            languages={languages}
            value={displayLang}
            onChange={(next) => {
              storeLanguage(next);
              setStoredLang(next);
            }}
          />
          <p className="loopback">127.0.0.1 · changes stay on this computer</p>
        </div>
      </header>
      <DuplicatesBanner programme={programme} onMerged={() => void reload()} />
      <div className="workspace">
        {mode === "records" ? (
          <RecordsColumn
            programme={programme}
            kind={kind}
            selectedId={kind === "conference" ? programme.conference.id : recordId}
            displayLang={displayLang}
            onKind={(next) => {
              setKind(next);
              setDraftDiagnostics(null);
              setRecordId(next === "conference" ? programme.conference.id : null);
            }}
            onSelect={(id) => {
              setRecordId(id);
              setDraftDiagnostics(null);
            }}
            onCreate={() => void onCreateKind()}
          />
        ) : (
          <Timetable
            programme={programme}
            day={activeDay}
            days={days}
            selectedId={sessionId}
            displayLang={displayLang}
            onDay={(next) => {
              setDay(next);
              setSessionId(null);
              setEditingId(null);
              setDraftDiagnostics(null);
            }}
            onSelect={openSession}
          />
        )}
        {mode === "records" && kind !== "contributions" && entity ? (
          <RecordForm
            key={`${kind}-${entity.id}`}
            kind={kind === "conference" ? "conference" : kind}
            record={entity}
            programme={programme}
            displayLang={displayLang}
            onSaved={onEntitySaved}
            onDraftDiagnostics={onDraftDiagnostics}
            onCreatePerson={createPerson}
            onDeleted={() => {
              setRecordId(null);
              void reload();
            }}
          />
        ) : formContribution && (mode === "timetable" || kind === "contributions") ? (
          <ContributionForm
            key={formContribution.id}
            programme={programme}
            contribution={formContribution}
            displayLang={displayLang}
            onBack={() => {
              setEditingId(null);
              setRecordId(null);
              setDraftDiagnostics(null);
            }}
            onSaved={onSaved}
            onDraftDiagnostics={onDraftDiagnostics}
            onCreatePerson={createPerson}
            onDeleted={() => {
              setEditingId(null);
              setRecordId(null);
              void reload();
            }}
          />
        ) : mode === "timetable" && session ? (
          <SessionDetail programme={programme} session={session} displayLang={displayLang} onOpen={openContribution} />
        ) : (
          <section className="detail">
            <h2>{mode === "records" ? "Record" : "Session"}</h2>
            <p className="quiet">
              {mode === "records" ? "Select a record to edit it." : "Select a block to list its talks in running order."}
            </p>
          </section>
        )}
        <DiagnosticsList
          diagnostics={diagnostics}
          programme={programme}
          displayLanguages={shown}
          activeId={editingId ?? (mode === "records" ? recordId : null)}
          onOpenMessage={onOpenMessage}
        />
      </div>
    </div>
  );
}
