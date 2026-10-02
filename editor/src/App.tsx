import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { loadProgramme } from "./api";
import { ContributionForm } from "./ContributionForm";
import { DiagnosticsList } from "./DiagnosticsList";
import { SessionDetail } from "./SessionDetail";
import { Timetable } from "./Timetable";
import type { Diagnostics, Programme, SaveResult } from "./types";
import { mentionsId, textOf } from "./text";

export function App() {
  const [programme, setProgramme] = useState<Programme | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [day, setDay] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftDiagnostics, setDraftDiagnostics] = useState<Diagnostics | null>(null);

  useEffect(() => {
    loadProgramme()
      .then((data) => {
        setProgramme(data);
        const first = [...data.sessions].sort((a, b) => a.date.localeCompare(b.date))[0];
        setDay(first?.date ?? null);
      })
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Could not load the programme");
      });
  }, []);

  const onDraftDiagnostics = useCallback((diagnostics: Diagnostics) => {
    setDraftDiagnostics(diagnostics);
  }, []);

  const days = useMemo(() => {
    if (!programme) {
      return [];
    }
    return [...new Set(programme.sessions.map((session) => session.date))].sort();
  }, [programme]);

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

  const languages = programme.conference.languages ?? [];
  const session = programme.sessions.find((item) => item.id === sessionId) ?? null;
  const contribution = programme.contributions.find((item) => item.id === editingId) ?? null;
  const diagnostics = editingId && draftDiagnostics ? draftDiagnostics : programme.diagnostics;

  function openSession(id: string) {
    setSessionId(id);
    setEditingId(null);
    setDraftDiagnostics(null);
  }

  function openContribution(id: string) {
    const talk = programme?.contributions.find((item) => item.id === id);
    if (!talk) {
      return;
    }
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

  function onSaved(result: SaveResult) {
    setProgramme((current) => {
      if (!current) {
        return current;
      }
      return {
        ...current,
        contributions: current.contributions.map((item) =>
          item.id === result.record.id ? result.record : item,
        ),
        placement: result.placement,
        diagnostics: result.diagnostics,
      };
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
    toast.message("That check is not a contribution or a session.");
  }

  return (
    <div className="app">
      <header className="top">
        <div>
          <p className="eyebrow">Local programme editor</p>
          <h1>{textOf(programme.conference.short_title, languages) || "Programme"}</h1>
        </div>
        <p className="loopback">127.0.0.1 · changes stay on this computer</p>
      </header>
      <div className="workspace">
        <Timetable
          programme={programme}
          day={activeDay}
          days={days}
          selectedId={sessionId}
          onDay={(next) => {
            setDay(next);
            setSessionId(null);
            setEditingId(null);
            setDraftDiagnostics(null);
          }}
          onSelect={openSession}
        />
        {contribution ? (
          <ContributionForm
            key={contribution.id}
            programme={programme}
            contribution={contribution}
            onBack={() => {
              setEditingId(null);
              setDraftDiagnostics(null);
            }}
            onSaved={onSaved}
            onDraftDiagnostics={onDraftDiagnostics}
          />
        ) : session ? (
          <SessionDetail programme={programme} session={session} onOpen={openContribution} />
        ) : (
          <section className="detail">
            <h2>Session</h2>
            <p className="quiet">Select a block to list its talks in running order.</p>
          </section>
        )}
        <DiagnosticsList
          diagnostics={diagnostics}
          activeId={editingId}
          onOpenMessage={onOpenMessage}
        />
      </div>
    </div>
  );
}
