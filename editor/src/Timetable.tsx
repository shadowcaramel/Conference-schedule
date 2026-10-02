import clsx from "clsx";
import { useEffect } from "react";
import type { Programme } from "./types";
import { clockMinutes, displayOrder, formatDay, sessionLabel, textOf } from "./text";

const PX_PER_MIN = 1.35;

type Props = {
  programme: Programme;
  day: string;
  days: string[];
  selectedId: string | null;
  displayLang: string;
  onDay: (day: string) => void;
  onSelect: (sessionId: string) => void;
  onSchedule: (contributionId: string) => void;
};

export function Timetable({ programme, day, days, selectedId, displayLang, onDay, onSelect, onSchedule }: Props) {
  const languages = displayOrder(programme.conference.languages ?? [], displayLang);
  const sessions = programme.sessions.filter((session) => session.date === day);
  const roomOrder = new Map(programme.rooms.map((room, index) => [room.id, index]));
  const roomIds = [...new Set(sessions.map((session) => session.room_id || ""))].sort((a, b) => {
    const ai = roomOrder.has(a) ? roomOrder.get(a)! : 1000;
    const bi = roomOrder.has(b) ? roomOrder.get(b)! : 1000;
    return ai - bi || a.localeCompare(b);
  });

  let startMin = 8 * 60;
  let endMin = 19 * 60;
  for (const session of sessions) {
    const start = clockMinutes(session.start);
    const placed = programme.placement.sessions[session.id];
    const end = clockMinutes(placed?.effective_end || session.end);
    if (start !== null) {
      startMin = Math.min(startMin, start);
    }
    if (end !== null) {
      endMin = Math.max(endMin, end);
    }
  }
  startMin = Math.floor(startMin / 60) * 60;
  endMin = Math.ceil(endMin / 60) * 60;
  const height = (endMin - startMin) * PX_PER_MIN;
  const hours: number[] = [];
  for (let minute = startMin; minute <= endMin; minute += 60) {
    hours.push(minute);
  }

  useEffect(() => {
    document.querySelector(".block.is-selected")?.scrollIntoView({ block: "nearest", inline: "nearest" });
  }, [selectedId, day]);

  const listed = new Set(programme.sessions.flatMap((session) => session.contribution_ids ?? []));
  const unscheduled = programme.contributions.filter((talk) => !talk.session_id || !listed.has(talk.id));

  const roomLabel = (roomId: string) => {
    if (!roomId) {
      return "No room";
    }
    const room = programme.rooms.find((item) => item.id === roomId);
    return textOf(room?.label, languages) || roomId;
  };

  return (
    <section className="timetable" aria-label="Timetable">
      <div className="days" role="tablist" aria-label="Days">
        {days.map((item) => (
          <button
            key={item}
            type="button"
            role="tab"
            data-date={item}
            aria-selected={item === day}
            className={clsx("day", "pressable", item === day && "is-selected")}
            onClick={() => onDay(item)}
          >
            {formatDay(item, displayLang)}
          </button>
        ))}
      </div>
      <div className="grid-scroll">
        <div
          className="grid"
          style={{
            gridTemplateColumns: `4.25rem repeat(${Math.max(roomIds.length, 1)}, minmax(9.5rem, 1fr))`,
          }}
        >
          <div className="corner" />
          {roomIds.map((roomId) => (
            <div key={roomId || "none"} className="room-head">
              {roomLabel(roomId)}
            </div>
          ))}
          <div className="gutter" style={{ height }}>
            {hours.slice(0, -1).map((minute) => (
              <span key={minute} className="hour" style={{ top: (minute - startMin) * PX_PER_MIN }}>
                {String(Math.floor(minute / 60)).padStart(2, "0")}:00
              </span>
            ))}
          </div>
          {roomIds.map((roomId) => (
              <div
              key={`col-${roomId || "none"}`}
              className="room-col"
              style={{
                height,
                ["--hour" as string]: `${60 * PX_PER_MIN}px`,
              }}
            >
              {sessions
                .filter((session) => (session.room_id || "") === roomId)
                .map((session) => {
                  const start = clockMinutes(session.start);
                  const placed = programme.placement.sessions[session.id];
                  const end = clockMinutes(placed?.effective_end || session.end);
                  if (start === null || end === null) {
                    return null;
                  }
                  const track = programme.tracks.find((item) => item.id === session.track_id);
                  const tone = track?.color || "slate";
                  return (
                    <button
                      key={session.id}
                      type="button"
                      className={clsx("block", `tone-${tone}`, selectedId === session.id && "is-selected")}
                      style={{
                        top: (start - startMin) * PX_PER_MIN,
                        height: Math.max((end - start) * PX_PER_MIN - 3, 22),
                      }}
                      onClick={() => onSelect(session.id)}
                    >
                      <span className="block-time">
                        {session.start}–{placed?.effective_end || session.end}
                      </span>
                      <span className="block-title">{sessionLabel(session, programme, languages)}</span>
                    </button>
                  );
                })}
            </div>
          ))}
        </div>
      </div>
      <section className="unscheduled" aria-label="Unscheduled talks">
        <h2>Unscheduled</h2>
        {unscheduled.length === 0 ? (
          <p className="quiet">Every talk is in a session.</p>
        ) : (
          <ul className="record-list">
            {unscheduled.map((talk) => (
              <li key={talk.id}>
                <div className="talk-row">
                  <button type="button" className="talk pressable" onClick={() => onSchedule(talk.id)}>
                    <span className="talk-title">{textOf(talk.title, languages) || talk.id}</span>
                    <span className="talk-meta">{talk.id}</span>
                  </button>
                  <button type="button" className="save pressable" onClick={() => onSchedule(talk.id)}>
                    Schedule
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  );
}
