export type TextValue = string | Record<string, string>;

export type Author = {
  person_id: string;
  affiliation_ids: string[];
  presenting: boolean;
};

export type Contribution = {
  id: string;
  format: "oral" | "poster" | string;
  track_id?: string;
  session_id?: string;
  order?: number;
  number?: string;
  title: TextValue;
  authors: Author[];
  duration_min?: number;
  start?: string;
  status: "ok" | "cancelled" | "moved" | string;
  topic_id?: string;
  note?: Record<string, string>;
  sponsor_id?: string;
  board?: string;
};

export type Person = {
  id: string;
  family?: string;
  given?: string;
  patronymic?: string;
  email?: string;
};

export type Organization = {
  id: string;
  name?: TextValue;
  url?: string;
  logo?: string;
};

export type Track = {
  id: string;
  short?: TextValue;
  full?: TextValue;
  color?: string;
};

export type Room = {
  id: string;
  label?: TextValue;
};

export type Session = {
  id: string;
  date: string;
  start: string;
  end: string;
  type: string;
  title?: TextValue;
  track_id?: string;
  room_id?: string;
  chairs?: Chair[];
  contribution_ids?: string[];
  note?: TextValue;
};

export type Conference = {
  id: string;
  title?: TextValue;
  short_title?: TextValue;
  languages: string[];
  session_types?: Record<string, TextValue>;
  date_start?: string;
  date_end?: string;
  city?: TextValue;
  venue?: TextValue;
  timezone?: string;
  website?: string;
  contact?: string;
  footnote?: TextValue;
  defaults?: { duration_min?: Record<string, number> };
};

export type Diagnostics = {
  errors: string[];
  warnings: string[];
};

export type ForRecord = {
  id: string;
  errors: string[];
  warnings: string[];
};

export type Slot = {
  date: string;
  start: string;
  end: string;
  session_id: string;
  duration: number | null;
  format: string;
};

export type SessionPlacement = {
  date: string;
  start: string;
  stated_end: string;
  effective_end: string;
  packed_end: string;
  type: string;
  track_id: string;
  room_id: string;
};

export type Placement = {
  sessions: Record<string, SessionPlacement>;
  contributions: Record<string, Slot>;
};

export type Resource = {
  id: string;
  contribution_id?: string;
  kind?: string;
  url?: string;
  lang?: string;
};

export type Change = {
  id: string;
  at?: string;
  text?: TextValue;
};

export type Chair = {
  person_id: string;
  label?: TextValue;
};

export type ReferenceHit = {
  kind: string;
  id: string;
  field: string;
};

export type DuplicateGroup = {
  family: string;
  initial: string;
  ids: string[];
};

export type DuplicateReport = {
  groups: DuplicateGroup[];
};

export type RecordKind =
  | "conference"
  | "tracks"
  | "rooms"
  | "sessions"
  | "contributions"
  | "people"
  | "organizations"
  | "resources"
  | "changes";

export type Programme = {
  conference: Conference;
  tracks: Track[];
  rooms: Room[];
  sessions: Session[];
  contributions: Contribution[];
  people: Person[];
  organizations: Organization[];
  resources: Resource[];
  changes: Change[];
  placement: Placement;
  diagnostics: Diagnostics;
  undo?: number;
};

export type StoredRecord = {
  id: string;
  [key: string]: unknown;
};

export type SaveResult = {
  record: StoredRecord;
  diagnostics: Diagnostics;
  for_record: ForRecord;
  placement: Placement;
  deleted?: { kind: string; id: string };
  undo?: number;
};

export type ValidateResult = {
  diagnostics: Diagnostics;
  for_record?: ForRecord;
};
