import type { Programme, SaveResult, ValidateResult } from "./types";

async function send<T>(method: string, path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const payload = (await response.json().catch(() => ({}))) as T & { error?: string };
  if (!response.ok) {
    throw new Error(payload.error || `Request failed (${response.status})`);
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
