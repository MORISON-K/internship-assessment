"""
routes.py
─────────
FastAPI route handlers.

Routes
  GET  /health                  – liveness probe
  GET  /languages               – list supported languages + voices
  POST /pipeline/text           – JSON body → full pipeline
  POST /pipeline/audio          – multipart/form-data → full pipeline
"""

from __future__ import annotations

import io
import logging

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, Response, StreamingResponse

from .constants import SUPPORTED_LANGUAGE_CODES
from .exceptions import UnsupportedLanguageError
from .audio_store import AudioStore
from .models import LanguagesResponse, PipelineResponse, TextPipelineRequest
from .pipeline import run_audio_pipeline, run_text_pipeline
from .sunbird_client import SunbirdClient

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Dependency: pull the shared client from app state ────────────────────────

def get_client(request: Request) -> SunbirdClient:
    return request.app.state.sunbird_client


def get_audio_store(request: Request) -> AudioStore:
    return request.app.state.audio_store


# ── Health ────────────────────────────────────────────────────────────────────


@router.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    """Simple liveness probe – returns 200 when the server is running."""
    return {"status": "ok"}


# ── Languages ─────────────────────────────────────────────────────────────────


@router.get(
    "/languages",
    response_model=LanguagesResponse,
    tags=["meta"],
    summary="List supported target languages",
)
async def list_languages() -> LanguagesResponse:
    """Return all languages that can be used as a translation target."""
    return LanguagesResponse.from_constants()


# ── Text pipeline ─────────────────────────────────────────────────────────────


@router.post(
    "/pipeline/text",
    response_model=PipelineResponse,
    tags=["pipeline"],
    summary="Run the full pipeline on typed/pasted text",
)
async def pipeline_text(
    body: TextPipelineRequest,
    client: SunbirdClient = Depends(get_client),
    audio_store: AudioStore = Depends(get_audio_store),
) -> PipelineResponse:
    """
    Accept plain text and a target language, then:
    1. Summarise the text with Sunflower.
    2. Translate the summary into the chosen Ugandan language.
    3. Generate a TTS audio clip of the translated summary.

    Returns transcript (null for text input), summary, translated summary,
    and a playable audio URL.
    """
    logger.info("POST /pipeline/text | lang=%s | len=%d", body.target_language, len(body.text))
    return await run_text_pipeline(
        text=body.text,
        target_language=body.target_language,
        client=client,
        audio_store=audio_store,
    )


# ── Audio pipeline ────────────────────────────────────────────────────────────


@router.post(
    "/pipeline/audio",
    response_model=PipelineResponse,
    tags=["pipeline"],
    summary="Run the full pipeline on an uploaded audio file",
)
async def pipeline_audio(
    audio: UploadFile = File(..., description="Audio file (mp3, wav, ogg, m4a, aac). Max 5 minutes."),
    target_language: str = Form(..., description="Target language code, e.g. 'lug'."),
    client: SunbirdClient = Depends(get_client),
    audio_store: AudioStore = Depends(get_audio_store),
) -> PipelineResponse:
    """
    Accept an audio file and a target language, then:
    1. Validate file type and duration (≤ 5 minutes).
    2. Transcribe the audio with Sunbird STT.
    3. Summarise the transcript with Sunflower.
    4. Translate the summary into the chosen Ugandan language.
    5. Generate a TTS audio clip of the translated summary.

    Returns transcript, summary, translated summary, and a playable audio URL.
    """
    # Normalise + validate language before reading the (potentially large) file
    lang_code = target_language.strip().lower()
    if lang_code not in SUPPORTED_LANGUAGE_CODES:
        raise UnsupportedLanguageError(lang_code)

    audio_bytes = await audio.read()
    filename = audio.filename or "upload.mp3"
    content_type = audio.content_type or "application/octet-stream"

    logger.info(
        "POST /pipeline/audio | file=%s | type=%s | size=%d | lang=%s",
        filename, content_type, len(audio_bytes), lang_code,
    )

    return await run_audio_pipeline(
        audio_bytes=audio_bytes,
        filename=filename,
        content_type=content_type,
        target_language=lang_code,
        client=client,
        audio_store=audio_store,
    )


# ── Generated audio playback ─────────────────────────────────────────────────


@router.get(
    "/audio/{audio_id}",
    tags=["pipeline"],
    summary="Fetch generated TTS audio (backend-proxied)",
)
async def get_generated_audio(
    audio_id: str,
    audio_store: AudioStore = Depends(get_audio_store),
) -> Response:
    item = audio_store.get(audio_id)
    if item is None:
        return JSONResponse(
            status_code=404,
            content={
                "detail": "Audio not found or expired. Please rerun the pipeline.",
                "error_type": "NotFound",
            },
        )

    return StreamingResponse(
        io.BytesIO(item.content),
        media_type=item.content_type,
        headers={"Cache-Control": "no-store"},
    )