type Props = {
  onChange: (file: File | null) => void;
};

export function AudioInput({ onChange }: Props) {
  return (
    <div className="flex flex-col gap-2">
      <label className="text-sm font-medium" htmlFor="audio">
        Audio file (max 5 minutes)
      </label>
      <input
        id="audio"
        type="file"
        accept="audio/*"
        className="block w-full text-sm"
        onChange={(e) => {
          onChange(e.target.files?.[0] || null);
        }}
      />
    </div>
  );
}
