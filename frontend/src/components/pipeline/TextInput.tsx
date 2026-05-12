type Props = {
  value: string;
  onChange: (value: string) => void;
};

export function TextInput({ value, onChange }: Props) {
  return (
    <div className="flex flex-col gap-2">
      <label className="text-sm font-medium" htmlFor="text">
        Text
      </label>
      <textarea
        id="text"
        className="min-h-32 w-full rounded-md border border-zinc-200 bg-white px-3 py-2 text-sm dark:border-zinc-800 dark:bg-black"
        placeholder="Paste or type text here…"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        maxLength={20000}
      />
    </div>
  );
}
