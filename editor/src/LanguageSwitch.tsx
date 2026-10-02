import { languageLabel, nextLanguage } from "./text";

type Props = {
  languages: string[];
  value: string;
  onChange: (next: string) => void;
};

/** Same control as the public site's `#btn-lang`: both codes, the active one bold. */
export function LanguageSwitch({ languages, value, onChange }: Props) {
  const next = nextLanguage(languages, value);
  const label = `Switch to ${languageLabel(next)}`;
  return (
    <button
      type="button"
      id="btn-lang"
      className="ctl lang pressable"
      data-lang={value}
      aria-label={label}
      title={label}
      onClick={() => onChange(next)}
    >
      {languages.map((code, index) => (
        <span key={code} className="lang-pair">
          {index > 0 ? (
            <span className="lang-sep" aria-hidden="true">
              ·
            </span>
          ) : null}
          <span data-code={code} className={code === value ? "is-active" : undefined}>
            {code.toUpperCase()}
          </span>
        </span>
      ))}
    </button>
  );
}
