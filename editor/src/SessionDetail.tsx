import type { Contribution, Programme, Session } from "./types";
import { personName, sessionLabel, textOf } from "./text";

type Props = {
  programme: Programme;
  session: Session;
  onOpen: (contributionId: string) => void;
};

export function SessionDetail({ programme, session, onOpen }: Props) {
  const languages = programme.conference.languages ?? [];
  const people = new Map(programme.people.map((person) => [person.id, person]));
  const contributions = new Map(programme.contributions.map((item) => [item.id, item]));
  const room = programme.rooms.find((item) => item.id === session.room_id);
  const placed = programme.placement.sessions[session.id];
  const ids = session.contribution_ids ?? [];

  return (
    <section className="detail" aria-label="Session">
      <header className="detail-head">
        <p className="eyebrow">{session.type}</p>
        <h2>{sessionLabel(session, programme)}</h2>
        <p className="meta">
          {textOf(room?.label, languages) || "No room"}
          {" · "}
          {session.start}–{placed?.effective_end || session.end}
        </p>
      </header>
      {ids.length === 0 ? (
        <p className="quiet">No talks in this session.</p>
      ) : (
        <ol className="talks">
          {ids.map((id) => {
            const talk = contributions.get(id);
            return (
              <li key={id}>
                <TalkRow
                  id={id}
                  talk={talk}
                  languages={languages}
                  speaker={speakerName(talk, people)}
                  start={programme.placement.contributions[id]?.start}
                  end={programme.placement.contributions[id]?.end}
                  onOpen={onOpen}
                />
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}

function speakerName(
  talk: Contribution | undefined,
  people: Map<string, Programme["people"][number]>,
): string {
  if (!talk) {
    return "";
  }
  const author = talk.authors.find((item) => item.presenting) ?? talk.authors[0];
  if (!author) {
    return "";
  }
  return personName(people.get(author.person_id));
}

function TalkRow({
  id,
  talk,
  languages,
  speaker,
  start,
  end,
  onOpen,
}: {
  id: string;
  talk: Contribution | undefined;
  languages: string[];
  speaker: string;
  start?: string;
  end?: string;
  onOpen: (id: string) => void;
}) {
  const title = talk ? textOf(talk.title, languages) : "Missing contribution";
  const when = start && end ? `${start}–${end}` : "Time not computed";
  return (
    <button type="button" className="talk pressable" onClick={() => onOpen(id)}>
      <span className="talk-time">{when}</span>
      <span className="talk-body">
        <span className={talk?.status === "cancelled" ? "talk-title is-cancelled" : "talk-title"}>{title}</span>
        <span className="talk-meta">
          {speaker || "No speaker"}
          {talk?.format === "poster" ? " · Poster" : ""}
          {talk?.status && talk.status !== "ok" ? ` · ${talk.status}` : ""}
        </span>
      </span>
    </button>
  );
}
