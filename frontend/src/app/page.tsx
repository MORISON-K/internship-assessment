"use client";

import { useEffect, useMemo, useState } from "react";

type InputMode = "text" | "audio";

type LanguageInfo = {
  code: string;
  name: string;
  tts_available: boolean;
};

type LanguagesResponse = {
  languages: LanguageInfo[];
};

type PipelineResponse = {
  input_type: "text" | "audio";
  original_text: string;
  transcript: string | null;
  detected_language: string | null;
  summary: string;
  target_language_code: string;
  target_language_name: string;
  translated_summary: string;
  audio_url: string;
};

type ApiError = {
  detail?: string;
  error_type?: string;
};

export default function Home() {
  const backendUrl = useMemo(() => {
    return (process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000").replace(
      /\/+$/,
      ""
    );
  }, []);

  const [inputMode, setInputMode] = useState<InputMode>("text");
  const [text, setText] = useState<string>("");
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [languages, setLanguages] = useState<LanguageInfo[]>([]);
  const [targetLanguage, setTargetLanguage] = useState<string>("lug");
  const [running, setRunning] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PipelineResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${backendUrl}/api/v1/languages`, {
          method: "GET",
        });
        if (!res.ok) {
          throw new Error(`Failed to load languages (HTTP ${res.status})`);
        }
        const data = (await res.json()) as LanguagesResponse;
        if (!cancelled) {
          setLanguages(data.languages || []);
          if (data.languages?.length && !data.languages.some((l) => l.code === targetLanguage)) {
            setTargetLanguage(data.languages[0].code);
          }
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load languages.");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [backendUrl, targetLanguage]);

  async function runPipeline() {
    setError(null);
    setResult(null);

    if (inputMode === "text") {
      const trimmed = text.trim();
      if (!trimmed) {
        setError("Please enter some text.");
        return;
      }
    }

    if (inputMode === "audio" && !audioFile) {
      setError("Please choose an audio file.");
      return;
    }

    setRunning(true);
    try {
      let res: Response;

      if (inputMode === "text") {
        res = await fetch(`${backendUrl}/api/v1/pipeline/text`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text, target_language: targetLanguage }),
        });
      } else {
        const form = new FormData();
        form.append("audio", audioFile as File);
        form.append("target_language", targetLanguage);
        res = await fetch(`${backendUrl}/api/v1/pipeline/audio`, {
          method: "POST",
          body: form,
        });
      }

      if (!res.ok) {
        let message = `Request failed (HTTP ${res.status}).`;
        try {
          const apiError = (await res.json()) as ApiError;
          if (apiError?.detail) message = apiError.detail;
        } catch {
          // ignore parse errors
        }
        throw new Error(message);
      }

      const data = (await res.json()) as PipelineResponse;
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed.");
    } finally {
      setRunning(false);
    }
  }

  const audioSrc = useMemo(() => {
    if (!result?.audio_url) return null;
    return result.audio_url.startsWith("/")
      ? `${backendUrl}${result.audio_url}`
      : result.audio_url;
  }, [backendUrl, result]);

  return (
    <div className="min-h-screen w-full bg-zinc-50 text-zinc-900 dark:bg-black dark:text-zinc-50">
      <main className="mx-auto w-full max-w-3xl px-6 py-10">
        <h1 className="text-2xl font-semibold">Sunbird AI GenAI Pipeline</h1>
        <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
          Input → (STT if audio) → Summarise → Translate → TTS
        </p>

        <section className="mt-8 rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <div className="text-sm font-medium">Input type</div>
              <div className="flex gap-4">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="radio"
                    name="inputMode"
                    value="text"
                    checked={inputMode === "text"}
                    onChange={() => setInputMode("text")}
                  />
                  Text
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="radio"
                    name="inputMode"
                    value="audio"
                    checked={inputMode === "audio"}
                    onChange={() => setInputMode("audio")}
                  />
                  Audio
                </label>
              </div>
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium" htmlFor="language">
                Target language
              </label>
              <select
                id="language"
                className="w-full rounded-md border border-zinc-200 bg-white px-3 py-2 text-sm dark:border-zinc-800 dark:bg-black"
                value={targetLanguage}
                onChange={(e) => setTargetLanguage(e.target.value)}
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

            {inputMode === "text" ? (
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium" htmlFor="text">
                  Text
                </label>
                <textarea
                  id="text"
                  className="min-h-32 w-full rounded-md border border-zinc-200 bg-white px-3 py-2 text-sm dark:border-zinc-800 dark:bg-black"
                  placeholder="Paste or type text here…"
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  maxLength={20000}
                />
              </div>
            ) : (
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
                    setAudioFile(e.target.files?.[0] || null);
                  }}
                />
              </div>
            )}

            <button
              type="button"
              onClick={runPipeline}
              disabled={running}
              className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 disabled:opacity-50 dark:bg-zinc-50 dark:text-black dark:hover:bg-zinc-200"
            >
              {running ? "Running…" : "Run pipeline"}
            </button>

            {error ? (
              <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900 dark:border-red-800 dark:bg-red-950/40 dark:text-red-100">
                {error}
              </div>
            ) : null}
          </div>
        </section>

        {result ? (
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
        ) : null}

        <section className="mt-8 text-xs text-zinc-600 dark:text-zinc-400">
          Backend: {backendUrl}
        </section>
      </main>
    </div>
  );
}
