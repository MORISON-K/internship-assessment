"use client";

import { useMemo, useState } from "react";

import { AudioInput } from "@/components/pipeline/AudioInput";
import { ErrorAlert } from "@/components/pipeline/ErrorAlert";
import { InputModeSelector } from "@/components/pipeline/InputModeSelector";
import { LanguageSelect } from "@/components/pipeline/LanguageSelect";
import { ResultsPanel } from "@/components/pipeline/ResultsPanel";
import { RunButton } from "@/components/pipeline/RunButton";
import { TextInput } from "@/components/pipeline/TextInput";
import { useLanguages } from "@/hooks/useLanguages";
import { usePipeline } from "@/hooks/usePipeline";
import { getBackendUrl } from "@/lib/backendUrl";
import type { InputMode } from "@/types/api";

export default function Home() {
  const backendUrl = useMemo(() => getBackendUrl(), []);

  const [inputMode, setInputMode] = useState<InputMode>("text");
  const [text, setText] = useState<string>("");
  const [audioFile, setAudioFile] = useState<File | null>(null);

  const {
    languages,
    targetLanguage,
    setTargetLanguage,
    error: languagesError,
  } = useLanguages(backendUrl, "lug");
  const { running, error: pipelineError, result, runPipeline } = usePipeline(backendUrl);

  const error = pipelineError ?? languagesError;

  return (
    <div className="min-h-screen w-full bg-zinc-50 text-zinc-900 dark:bg-black dark:text-zinc-50">
      <main className="mx-auto w-full max-w-3xl px-6 py-10">
        <h1 className="text-2xl font-semibold">Sunbird AI GenAI Pipeline</h1>
        <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
          Input → (STT if audio) → Summarise → Translate → TTS
        </p>

        <section className="mt-8 rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
          <div className="flex flex-col gap-4">
            <InputModeSelector inputMode={inputMode} onChange={setInputMode} />

            <LanguageSelect
              languages={languages}
              targetLanguage={targetLanguage}
              onChange={setTargetLanguage}
            />

            {inputMode === "text" ? (
              <TextInput value={text} onChange={setText} />
            ) : (
              <AudioInput onChange={setAudioFile} />
            )}

            <RunButton
              running={running}
              onClick={() =>
                runPipeline({
                  inputMode,
                  text,
                  audioFile,
                  targetLanguage,
                })
              }
            />

            {error ? (
              <ErrorAlert message={error} />
            ) : null}
          </div>
        </section>

        {result ? <ResultsPanel backendUrl={backendUrl} result={result} /> : null}

        <section className="mt-8 text-xs text-zinc-600 dark:text-zinc-400">
          Backend: {backendUrl}
        </section>
      </main>
    </div>
  );
}
