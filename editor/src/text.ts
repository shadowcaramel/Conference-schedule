import type { Person, Programme, Session, TextValue } from "./types";

const LANGUAGE_NAMES: Record<string, string> = {
  en: "English",
  ru: "Russian",
};

export function languageLabel(code: string): string {
  return LANGUAGE_NAMES[code] ?? code;
}

/** Pick the first non-empty string in ``conference.languages`` order. */
export function textOf(value: TextValue | undefined, languages: string[]): string {
  if (typeof value === "string") {
    return value;
  }
  if (!value || typeof value !== "object") {
    return "";
  }
  for (const lang of languages) {
    const item = value[lang];
    if (typeof item === "string" && item.trim()) {
      return item;
    }
  }
  for (const item of Object.values(value)) {
    if (typeof item === "string" && item.trim()) {
      return item;
    }
  }
  return "";
}

export function personName(person: Person | undefined): string {
  if (!person) {
    return "";
  }
  return [person.family, person.given, person.patronymic].filter(Boolean).join(" ");
}

export function sessionLabel(session: Session, programme: Programme): string {
  const languages = programme.conference.languages ?? [];
  const title = textOf(session.title, languages);
  if (title) {
    return title;
  }
  const track = programme.tracks.find((item) => item.id === session.track_id);
  const trackName = textOf(track?.short, languages);
  if (trackName) {
    return trackName;
  }
  return textOf(programme.conference.session_types?.[session.type], languages) || session.type;
}

export function formatDay(iso: string): string {
  const date = new Date(`${iso}T12:00:00`);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return new Intl.DateTimeFormat("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
  }).format(date);
}

export function clockMinutes(value: string): number | null {
  const match = /^(\d{2}):(\d{2})$/.exec(value);
  if (!match) {
    return null;
  }
  const hours = Number(match[1]);
  const minutes = Number(match[2]);
  if (hours > 23 || minutes > 59) {
    return null;
  }
  return hours * 60 + minutes;
}

export function mentionsId(message: string, recordId: string): boolean {
  if (!recordId) {
    return false;
  }
  const escaped = recordId.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`(?<![A-Za-z0-9-])${escaped}(?![A-Za-z0-9-])`).test(message);
}
