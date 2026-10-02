import { useEffect, useState } from "react";
import { toast } from "sonner";
import { loadDuplicates, mergePeople } from "./api";
import type { DuplicateGroup, Programme } from "./types";
import { personName } from "./text";

type Props = {
  programme: Programme;
  onMerged: () => void;
};

export function DuplicatesBanner({ programme, onMerged }: Props) {
  const [groups, setGroups] = useState<DuplicateGroup[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    loadDuplicates()
      .then((report) => {
        if (!cancelled) {
          setGroups(report.groups);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          toast.error(error instanceof Error ? error.message : "Could not check for duplicate people");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [programme]);

  if (groups.length === 0) {
    return null;
  }

  async function merge(keep: string, drop: string) {
    setBusy(true);
    try {
      const result = await mergePeople(keep, drop);
      toast.success(`Merged ${drop} into ${keep} (${result.rewritten} references)`);
      onMerged();
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : "Merge failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="duplicates" aria-label="Likely duplicate people">
      <h2>Likely duplicate people</h2>
      {groups.map((group) => {
        const keep = group.ids[0];
        const keepPerson = programme.people.find((person) => person.id === keep);
        return (
          <div key={group.ids.join("-")} className="duplicate-group">
            <p>
              Same family “{group.family}” and initial “{group.initial || "—"}”.
            </p>
            <ul>
              {group.ids.map((id) => {
                const person = programme.people.find((item) => item.id === id);
                return (
                  <li key={id}>
                    <span>
                      {personName(person) || id} · {id}
                    </span>
                    {id !== keep ? (
                      <button type="button" className="text-button pressable" disabled={busy} onClick={() => merge(keep, id)}>
                        Merge into {personName(keepPerson) || keep}
                      </button>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          </div>
        );
      })}
    </section>
  );
}
