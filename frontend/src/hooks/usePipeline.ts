import { useCallback, useState } from "react";

import type { InputMode, PipelineResponse } from "@/types/api";
import { runAudioPipeline, runTextPipeline } from "@/lib/pipelineApi";

type RunPipelineArgs = {
  inputMode: InputMode;
  text: string;
  audioFile: File | null;
  targetLanguage: string;
};

type UsePipelineResult = {
  running: boolean;
  error: string | null;
  result: PipelineResponse | null;
  runPipeline: (args: RunPipelineArgs) => Promise<void>;
};

export function usePipeline(backendUrl: string): UsePipelineResult {
  const [running, setRunning] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PipelineResponse | null>(null);

  const runPipeline = useCallback(
    async (args: RunPipelineArgs) => {
      setError(null);
      setResult(null);

      if (args.inputMode === "text") {
        const trimmed = args.text.trim();
        if (!trimmed) {
          setError("Please enter some text.");
          return;
        }
      }

      if (args.inputMode === "audio" && !args.audioFile) {
        setError("Please choose an audio file.");
        return;
      }

      setRunning(true);
      try {
        const data =
          args.inputMode === "text"
            ? await runTextPipeline(backendUrl, {
                text: args.text,
                target_language: args.targetLanguage,
              })
            : await runAudioPipeline(backendUrl, {
                audioFile: args.audioFile as File,
                target_language: args.targetLanguage,
              });

        setResult(data);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Request failed.");
      } finally {
        setRunning(false);
      }
    },
    [backendUrl]
  );

  return { running, error, result, runPipeline };
}
