"""
pipeline.py
───────────
Orchestrates the full processing pipeline:

  Audio  ──STT──►  Text  ──summarise──►  Summary  ──translate──►  Translation
                                                                        │
                                                                      TTS
                                                                        │
                                                                    audio_url

  Text   ──────►  Text  ──summarise──►  Summary  ──translate──►  Translation
                                                                        │
                                                                      TTS
                                                                        │
                                                                    audio_url

The two entry points (run_text_pipeline / run_audio_pipeline) are intentionally
thin: they delegate every AI call to SunbirdClient and every validation to
audio_utils, then assemble the final PipelineResponse.
"""

from __future__ import annotations

import logging

from .audio_utils import validate_audio
from .audio_store import AudioStore
from .models import PipelineResponse
from .sunbird_client import SunbirdClient

logger = logging.getLogger(__name__)


async def run_text_pipeline(
    text: str,
    target_language: str,
    client: SunbirdClient,
    audio_store: AudioStore,
) -> PipelineResponse:
    """
    Execute the pipeline for a plain-text input.

    Steps: summarise → translate → TTS
    """
    logger.info(
        "Text pipeline start. lang=%s, input_len=%d", target_language, len(text)
    )

    # Step 3 – Summarise
    summary = await client.summarise(text)

    # Step 4 – Translate
    translated_summary = await client.translate(summary, target_language)

    # Step 5 – TTS
    upstream_audio_url = await client.synthesise_speech(translated_summary, target_language)
    audio_bytes, content_type = await client.download_audio(upstream_audio_url)
    audio_id = audio_store.put(audio_bytes, content_type)
    audio_url = f"/api/v1/audio/{audio_id}"

    from .constants import LANGUAGES
    lang = LANGUAGES[target_language]

    logger.info("Text pipeline complete.")
    return PipelineResponse(
        input_type="text",
        original_text=text,
        transcript=None,
        detected_language=None,
        summary=summary,
        target_language_code=lang.code,
        target_language_name=lang.name,
        translated_summary=translated_summary,
        audio_url=audio_url,
    )


async def run_audio_pipeline(
    audio_bytes: bytes,
    filename: str,
    content_type: str,
    target_language: str,
    client: SunbirdClient,
    audio_store: AudioStore,
) -> PipelineResponse:
    """
    Execute the pipeline for an uploaded audio file.

    Steps: validate → STT → summarise → translate → TTS
    """
    logger.info(
        "Audio pipeline start. file=%s, lang=%s, size=%d bytes",
        filename, target_language, len(audio_bytes),
    )

    # Step 1 – Validate audio (raises on failure)
    validate_audio(audio_bytes, filename, content_type)

    # Step 2 – Transcribe
    stt_output = await client.transcribe(audio_bytes, filename, content_type)
    transcript: str = stt_output.get("text", "")
    detected_language: str | None = stt_output.get("language")

    if not transcript.strip():
        from .exceptions import TranscriptionError
        raise TranscriptionError(
            "/tasks/stt", 200, "STT returned an empty transcript."
        )

    # Step 3 – Summarise the transcript
    summary = await client.summarise(transcript)

    # Step 4 – Translate
    translated_summary = await client.translate(summary, target_language)

    # Step 5 – TTS
    upstream_audio_url = await client.synthesise_speech(translated_summary, target_language)
    generated_audio_bytes, generated_content_type = await client.download_audio(upstream_audio_url)
    audio_id = audio_store.put(generated_audio_bytes, generated_content_type)
    audio_url = f"/api/v1/audio/{audio_id}"

    from .constants import LANGUAGES
    lang = LANGUAGES[target_language]

    logger.info("Audio pipeline complete.")
    return PipelineResponse(
        input_type="audio",
        original_text=transcript,
        transcript=transcript,
        detected_language=detected_language,
        summary=summary,
        target_language_code=lang.code,
        target_language_name=lang.name,
        translated_summary=translated_summary,
        audio_url=audio_url,
    )