import type { ApiError, LanguagesResponse, PipelineResponse } from "@/types/api";

type TextPipelinePayload = {
  text: string;
  target_language: string;
};

type AudioPipelinePayload = {
  audioFile: File;
  target_language: string;
};

async function readErrorMessage(res: Response): Promise<string> {
  let message = `Request failed (HTTP ${res.status}).`;
  try {
    const apiError = (await res.json()) as ApiError;
    if (apiError?.detail) message = apiError.detail;
  } catch {
    // ignore parse errors
  }
  return message;
}

export async function getLanguages(backendUrl: string): Promise<LanguagesResponse> {
  const res = await fetch(`${backendUrl}/api/v1/languages`, { method: "GET" });
  if (!res.ok) {
    throw new Error(await readErrorMessage(res));
  }
  return (await res.json()) as LanguagesResponse;
}

export async function runTextPipeline(
  backendUrl: string,
  payload: TextPipelinePayload
): Promise<PipelineResponse> {
  const res = await fetch(`${backendUrl}/api/v1/pipeline/text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error(await readErrorMessage(res));
  }

  return (await res.json()) as PipelineResponse;
}

export async function runAudioPipeline(
  backendUrl: string,
  payload: AudioPipelinePayload
): Promise<PipelineResponse> {
  const form = new FormData();
  form.append("audio", payload.audioFile);
  form.append("target_language", payload.target_language);

  const res = await fetch(`${backendUrl}/api/v1/pipeline/audio`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    throw new Error(await readErrorMessage(res));
  }

  return (await res.json()) as PipelineResponse;
}
