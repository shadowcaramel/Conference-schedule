import type { DuplicateReport, Programme, ReferenceHit, SaveResult, ValidateResult } from "./types";

export class ApiError extends Error {
  status: number;
  references: ReferenceHit[];
  offer?: string;

  constructor(status: number, message: string, payload: { references?: ReferenceHit[]; offer?: string }) {
    super(message);
    this.status = status;
    this.references = payload.references ?? [];
    this.offer = payload.offer;
  }
}

async function send<T>(method: string, path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const payload = (await response.json().catch(() => ({}))) as T & {
    error?: string;
    references?: ReferenceHit[];
    offer?: string;
  };
  if (!response.ok) {
    throw new ApiError(response.status, payload.error || `Request failed (${response.status})`, payload);
  }
  return payload;
}

export function loadProgramme(): Promise<Programme> {
  return send<Programme>("GET", "/api/data");
}

export function saveContribution(record: Record<string, unknown>): Promise<SaveResult> {
  const id = encodeURIComponent(String(record.id ?? ""));
  return send<SaveResult>("PUT", `/api/records/contributions/${id}`, record);
}

export function validateContribution(record: Record<string, unknown>): Promise<ValidateResult> {
  return send<ValidateResult>("POST", "/api/validate", {
    kind: "contributions",
    record,
  });
}

export function saveRecord(kind: string, record: Record<string, unknown>): Promise<SaveResult> {
  const id = encodeURIComponent(String(record.id ?? ""));
  return send<SaveResult>("PUT", `/api/records/${kind}/${id}`, record);
}

export function createRecord(kind: string, record: Record<string, unknown>): Promise<SaveResult> {
  return send<SaveResult>("POST", `/api/records/${kind}`, record);
}

export function validateRecord(kind: string, record: Record<string, unknown>): Promise<ValidateResult> {
  return send<ValidateResult>("POST", "/api/validate", { kind, record });
}

export function deleteRecord(kind: string, id: string, force = false): Promise<SaveResult> {
  const path = `/api/records/${encodeURIComponent(kind)}/${encodeURIComponent(id)}${force ? "?force=1" : ""}`;
  return send<SaveResult>("DELETE", path);
}

export function loadDuplicates(): Promise<DuplicateReport> {
  return send<DuplicateReport>("GET", "/api/duplicates");
}

export function mergePeople(keep: string, drop: string): Promise<{ kept: string; dropped: string; rewritten: number }> {
  return send("POST", "/api/people/merge", { keep, drop });
}

export function scheduleTalk(body: {
  contribution_id: string;
  session_id: string;
  index?: number;
}): Promise<Programme> {
  return send<Programme>("POST", "/api/schedule", body);
}

export function reorderTalk(contributionId: string, direction: "up" | "down"): Promise<Programme> {
  return send<Programme>("POST", "/api/reorder", { contribution_id: contributionId, direction });
}

export function undoEdit(): Promise<Programme> {
  return send<Programme>("POST", "/api/undo");
}

export type ChangeRequest = {
  kind: "cancelled" | "moved" | "retimed";
  contribution_id?: string;
  session_id?: string;
  previous_start?: string;
  previous_end?: string;
};

export function proposeChange(body: ChangeRequest): Promise<{ proposal: { at: string; text: Record<string, string> } }> {
  return send("POST", "/api/changes/propose", body);
}

export type ReviewReport = {
  summary: string[];
  diff: string;
  errors: string[];
  warnings: string[];
};

export type PublishResult = {
  branch: string;
  compare_url: string;
  pull_request: string | null;
  detail?: string;
};

export function loadReview(): Promise<ReviewReport> {
  return send<ReviewReport>("GET", "/api/review");
}

export function openPreview(): Promise<{ url: string }> {
  return send("POST", "/api/preview", {});
}

export function publishProgramme(): Promise<PublishResult> {
  return send<PublishResult>("POST", "/api/publish", {});
}

export function publishStatus(prUrl: string): Promise<{ state: string; checks: { name: string; status: string }[]; detail: string }> {
  return send("GET", `/api/publish/status?pr=${encodeURIComponent(prUrl)}`);
}
