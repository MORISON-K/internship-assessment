import { useEffect, useState } from "react";

import type { LanguageInfo } from "@/types/api";
import { getLanguages } from "@/lib/pipelineApi";

type UseLanguagesResult = {
  languages: LanguageInfo[];
  targetLanguage: string;
  setTargetLanguage: (lang: string) => void;
  loading: boolean;
  error: string | null;
};

export function useLanguages(
  backendUrl: string,
  initialTargetLanguage: string
): UseLanguagesResult {
  const [languages, setLanguages] = useState<LanguageInfo[]>([]);
  const [targetLanguage, setTargetLanguage] = useState<string>(initialTargetLanguage);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getLanguages(backendUrl);
        if (cancelled) return;

        const nextLanguages = data.languages || [];
        setLanguages(nextLanguages);

        if (
          nextLanguages.length &&
          !nextLanguages.some((l) => l.code === targetLanguage)
        ) {
          setTargetLanguage(nextLanguages[0].code);
        }
      } catch (e) {
        if (!cancelled) {
          setLanguages([]);
          setError(e instanceof Error ? e.message : "Failed to load languages.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }

    };

    void run();

    return () => {
      cancelled = true;
    };
    // Intentionally fetch only when backendUrl changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [backendUrl]);

  return {
    languages,
    targetLanguage,
    setTargetLanguage,
    loading,
    error,
  };
}
