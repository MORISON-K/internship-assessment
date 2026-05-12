import type { LanguageInfo } from "@/types/api";

type Props = {
  languages: LanguageInfo[];
  targetLanguage: string;
  onChange: (lang: string) => void;
};

export function LanguageSelect({ languages, targetLanguage, onChange }: Props) {
  return (
    <div className="flex flex-col gap-2">
      <label className="text-sm font-medium" htmlFor="language">
        Target language
      </label>
      <select
        id="language"
        className="w-full rounded-md border border-zinc-200 bg-white px-3 py-2 text-sm dark:border-zinc-800 dark:bg-black"
        value={targetLanguage}
        onChange={(e) => onChange(e.target.value)}
      >
        {languages.length ? (
          languages.map((l) => (
            <option key={l.code} value={l.code}>
              {l.name} ({l.code})
            </option>
          ))
        ) : (
          <option value="lug">Luganda (lug)</option>
        )}
      </select>
    </div>
  );
}
