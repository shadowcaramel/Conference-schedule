/** Map a string or `{lang: text}` value onto the conference languages. */
export function languageMap(value: unknown, languages: string[], copyString: boolean): Record<string, string> {
  if (typeof value === "string") {
    return Object.fromEntries(languages.map((lang) => [lang, copyString ? value : ""]));
  }
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    return Object.fromEntries(
      languages.map((lang) => [lang, typeof record[lang] === "string" ? record[lang] : ""]),
    );
  }
  return Object.fromEntries(languages.map((lang) => [lang, ""]));
}

/** Store bilingual text as `{ru, en, ...}`. Empty text becomes undefined so dataio can drop it. */
export function bilingualPayload(byLang: Record<string, string>, languages: string[]): Record<string, string> | undefined {
  const out: Record<string, string> = {};
  let any = false;
  for (const lang of languages) {
    out[lang] = byLang[lang] ?? "";
    if (out[lang].trim()) {
      any = true;
    }
  }
  if (!any) {
    return undefined;
  }
  if (!("ru" in out)) {
    out.ru = "";
  }
  if (!("en" in out)) {
    out.en = "";
  }
  return out;
}
