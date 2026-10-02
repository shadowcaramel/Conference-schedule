import { useState } from "react";
import { toast } from "sonner";
import { ApiError, deleteRecord } from "./api";
import type { Programme, ReferenceHit } from "./types";
import { displayOrder, sessionLabel, textOf } from "./text";

type Props = {
  kind: string;
  id: string;
  programme: Programme;
  displayLang: string;
  contribution?: boolean;
  onDeleted: () => void;
  onMarkCancelled?: () => Promise<void>;
};

function describe(hit: ReferenceHit, programme: Programme, languages: string[]): string {
  if (hit.kind === "sessions") {
    const session = programme.sessions.find((item) => item.id === hit.id);
    const label = session ? sessionLabel(session, programme, languages) : hit.id;
    return `Session ${label} · ${hit.field}`;
  }
  if (hit.kind === "contributions") {
    const talk = programme.contributions.find((item) => item.id === hit.id);
    const title = talk ? textOf(talk.title, languages) || talk.id : hit.id;
    return `Talk ${title} · ${hit.field}`;
  }
  if (hit.kind === "resources") {
    return `Resource ${hit.id} · ${hit.field}`;
  }
  return `${hit.kind} ${hit.id} · ${hit.field}`;
}

export function DeleteControl({ kind, id, programme, displayLang, contribution, onDeleted, onMarkCancelled }: Props) {
  const languages = displayOrder(programme.conference.languages ?? [], displayLang);
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [references, setReferences] = useState<ReferenceHit[]>([]);
  const [offerCancelled, setOfferCancelled] = useState(false);
  const [busy, setBusy] = useState(false);

  async function ask() {
    setBusy(true);
    try {
      await deleteRecord(kind, id, false);
      toast.success("Deleted");
      onDeleted();
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 409) {
        setMessage(error.message);
        setReferences(error.references);
        setOfferCancelled(error.offer === "cancelled");
        setOpen(true);
      } else {
        toast.error(error instanceof Error ? error.message : "Delete failed");
      }
    } finally {
      setBusy(false);
    }
  }

  async function forceDelete() {
    setBusy(true);
    try {
      await deleteRecord(kind, id, true);
      toast.success("Deleted");
      setOpen(false);
      onDeleted();
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 409) {
        setMessage(error.message);
        setReferences(error.references);
        setOfferCancelled(error.offer === "cancelled");
      } else {
        toast.error(error instanceof Error ? error.message : "Delete failed");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="danger-zone">
      <button type="button" className="danger-button pressable" onClick={ask} disabled={busy}>
        Delete
      </button>
      {open ? (
        <div className="dialog-backdrop" role="presentation">
          <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="delete-title">
            <h3 id="delete-title">Delete {id}</h3>
            <p>{message}</p>
            {references.length > 0 ? (
              <>
                <p className="quiet">These records still point at it:</p>
                <ul className="ref-list">
                  {references.map((hit) => (
                    <li key={`${hit.kind}-${hit.id}-${hit.field}`}>{describe(hit, programme, languages)}</li>
                  ))}
                </ul>
              </>
            ) : null}
            <div className="dialog-actions">
              <button type="button" className="text-button pressable" onClick={() => setOpen(false)}>
                Keep
              </button>
              {contribution && offerCancelled && onMarkCancelled ? (
                <button
                  type="button"
                  className="save pressable"
                  disabled={busy}
                  onClick={() => {
                    setBusy(true);
                    onMarkCancelled()
                      .then(() => setOpen(false))
                      .catch((error: unknown) => {
                        toast.error(error instanceof Error ? error.message : "Could not mark cancelled");
                      })
                      .finally(() => setBusy(false));
                  }}
                >
                  Mark cancelled
                </button>
              ) : null}
              {references.length === 0 ? (
                <button type="button" className="danger-button pressable" disabled={busy} onClick={forceDelete}>
                  Delete anyway
                </button>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
