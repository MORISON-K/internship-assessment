type Props = {
  message: string;
};

export function ErrorAlert({ message }: Props) {
  return (
    <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900 dark:border-red-800 dark:bg-red-950/40 dark:text-red-100">
      {message}
    </div>
  );
}
