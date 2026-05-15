export type InputMode = "text" | "audio";

export type LanguageInfo = {
  code: string;
  name: string;
  tts_available: boolean;
};

export type LanguagesResponse = {
  languages: LanguageInfo[];
};

export type PipelineResponse = {
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

export type ApiError = {
  detail?: string;
  error_type?: string;
};
