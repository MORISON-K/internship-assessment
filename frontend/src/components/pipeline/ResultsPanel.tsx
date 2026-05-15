import { useMemo } from "react";

import type { PipelineResponse } from "@/types/api";
import { resolveBackendUrl } from "@/lib/backendUrl";

type Props = {
  backendUrl: string;
  result: PipelineResponse;
};

export function ResultsPanel({ backendUrl, result }: Props) {
  const audioSrc = useMemo(() => {
    if (!result.audio_url) return null;
    return resolveBackendUrl(backendUrl, result.audio_url);
  }, [backendUrl, result.audio_url]);

  return (
    <section className="mt-8 rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
      <h2 className="text-lg font-semibold">Results</h2>

      <div className="mt-4 grid gap-4">
        <div>
          <div className="text-sm font-medium">Original text</div>
          <pre className="mt-1 whitespace-pre-wrap rounded-md bg-zinc-100 p-3 text-sm dark:bg-zinc-900">
            {result.original_text}
          </pre>
        </div>

        {result.input_type === "audio" ? (
          <div>
            <div className="text-sm font-medium">Transcript</div>
            <pre className="mt-1 whitespace-pre-wrap rounded-md bg-zinc-100 p-3 text-sm dark:bg-zinc-900">
              {result.transcript || "(empty)"}
            </pre>
            {result.detected_language ? (
              <div className="mt-1 text-xs text-zinc-600 dark:text-zinc-400">
                Detected language: {result.detected_language}
              </div>
            ) : null}
          </div>
        ) : null}

        <div>
          <div className="text-sm font-medium">Summary (English)</div>
          <pre className="mt-1 whitespace-pre-wrap rounded-md bg-zinc-100 p-3 text-sm dark:bg-zinc-900">
            {result.summary}
          </pre>
        </div>

        <div>
          <div className="text-sm font-medium">
            Translated summary ({result.target_language_name})
          </div>
          <pre className="mt-1 whitespace-pre-wrap rounded-md bg-zinc-100 p-3 text-sm dark:bg-zinc-900">
            {result.translated_summary}
          </pre>
        </div>

        <div>
          <div className="text-sm font-medium">Generated audio</div>
          {audioSrc ? (
            <audio className="mt-2 w-full" controls src={audioSrc} />
          ) : (
            <div className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
              No audio URL returned.
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
