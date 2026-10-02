import { useState } from "react";
import { toast } from "sonner";
import { languageLabel } from "./text";

export type ChangeProposal = {
  at: string;
  text: Record<string, string>;
};

type Props = {
  proposal: ChangeProposal;
  languages: string[];
  onSave: (body: { at: string; text: Record<string, string> }) => Promise<void>;
  onSkip: () => void;
};

export function ChangePrompt({ proposal, languages, onSave, onSkip }: Props) {
  const [at, setAt] = useState(proposal.at);
  const [text, setText] = useState(proposal.text);
  const [busy, setBusy] = useState(false);

  return (
    <div className="dialog-backdrop" role="presentation">
      <form
        className="dialog"
        id="change-prompt"
        role="dialog"
        aria-modal="true"
        aria-labelledby="change-title"
        onSubmit={(event) => {
          event.preventDefault();
          setBusy(true);
          onSave({ at, text })
            .catch((error: unknown) => {
              toast.error(error instanceof Error ? error.message : "Could not add the changes-feed entry");
            })
            .finally(() => setBusy(false));
        }}
      >
        <h3 id="change-title">Add a changes-feed entry?</h3>
        <p>Write a short note in each conference language, or skip it. Skipping leaves the programme change in place and adds nothing to the feed.</p>
        <label className="field">
          <span>When</span>
          <input value={at} onChange={(event) => setAt(event.target.value)} />
        </label>
        {languages.map((lang) => (
          <label className="field" key={lang}>
            <span>Text · {languageLabel(lang)}</span>
            <textarea
              rows={3}
              value={text[lang] ?? ""}
              onChange={(event) => setText((current) => ({ ...current, [lang]: event.target.value }))}
            />
          </label>
        ))}
        <div className="dialog-actions">
          <button type="button" className="text-button pressable" onClick={onSkip} disabled={busy}>
            Skip
          </button>
          <button type="submit" className="save pressable" disabled={busy}>
            {busy ? "Adding…" : "Add to the feed"}
          </button>
        </div>
      </form>
    </div>
  );
}
