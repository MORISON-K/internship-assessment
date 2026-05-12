import type { InputMode } from "@/types/api";

type Props = {
  inputMode: InputMode;
  onChange: (mode: InputMode) => void;
};

export function InputModeSelector({ inputMode, onChange }: Props) {
  return (
    <div className="flex flex-col gap-2">
      <div className="text-sm font-medium">Input type</div>
      <div className="flex gap-4">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="radio"
            name="inputMode"
            value="text"
            checked={inputMode === "text"}
            onChange={() => onChange("text")}
          />
          Text
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="radio"
            name="inputMode"
            value="audio"
            checked={inputMode === "audio"}
            onChange={() => onChange("audio")}
          />
          Audio
        </label>
      </div>
    </div>
  );
}
