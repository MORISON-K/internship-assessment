type Props = {
  running: boolean;
  onClick: () => void;
};

export function RunButton({ running, onClick }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={running}
      className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 disabled:opacity-50 dark:bg-zinc-50 dark:text-black dark:hover:bg-zinc-200"
    >
      {running ? "Running…" : "Run pipeline"}
    </button>
  );
}
