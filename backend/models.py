"""
Pydantic v2 schemas for every FastAPI request and response shape.
Keeping them in one module avoids circular imports and makes the
OpenAPI spec easy to review.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .constants import SUPPORTED_LANGUAGE_CODES, LANGUAGES


# ── Shared sub-models ─────────────────────────────────────────────────────────


class LanguageInfo(BaseModel):
    """Serialisable description of a single supported language."""

    code: str
    name: str
    tts_available: bool


# ── /pipeline/text  request ───────────────────────────────────────────────────


class TextPipelineRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=20_000,
        description="Source text to summarise and translate.",
    )
    target_language: str = Field(
        ...,
        description="ISO-like Sunbird language code, e.g. 'lug'.",
    )

    @field_validator("target_language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in SUPPORTED_LANGUAGE_CODES:
            raise ValueError(
                f"'{v}' is not a supported language. "
                f"Choose from: {sorted(SUPPORTED_LANGUAGE_CODES)}"
            )
        return v

    @field_validator("text")
    @classmethod
    def strip_text(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("text must not be blank or whitespace only.")
        return stripped


# ── /pipeline/audio  (multipart) is handled via FastAPI's Form + UploadFile,
#    so no dedicated request model is needed – validation lives in the route.


# ── Shared pipeline response ──────────────────────────────────────────────────


class PipelineResponse(BaseModel):
    """
    Unified response returned by both /pipeline/text and /pipeline/audio.
    Fields that don't apply (e.g. transcript for text input) are None.
    """

    # Step 1 – original input echo
    input_type: Literal["text", "audio"]
    original_text: str = Field(description="Typed text, or STT transcript of audio.")

    # Step 2 – transcript (audio path only)
    transcript: str | None = Field(
        default=None,
        description="Raw STT output. Null when input_type='text'.",
    )
    detected_language: str | None = Field(
        default=None,
        description="Language code detected by the STT model.",
    )

    # Step 3 – summary
    summary: str = Field(description="English summary produced by Sunflower.")

    # Step 4 – translation
    target_language_code: str
    target_language_name: str
    translated_summary: str = Field(
        description="Summary translated into the target language."
    )

    # Step 5 – TTS
    audio_url: str = Field(
        description="URL to the generated audio clip (served by this backend)."
    )


# ── /languages response ───────────────────────────────────────────────────────


class LanguagesResponse(BaseModel):
    languages: list[LanguageInfo]

    @classmethod
    def from_constants(cls) -> "LanguagesResponse":
        return cls(
            languages=[
                LanguageInfo(
                    code=lang.code,
                    name=lang.name,
                    tts_available=lang.tts_speaker_id is not None,
                )
                for lang in LANGUAGES.values()
            ]
        )


# ── Generic error response (rendered by the exception handlers) ───────────────


class ErrorResponse(BaseModel):
    detail: str
    error_type: str = Field(description="Python exception class name.")