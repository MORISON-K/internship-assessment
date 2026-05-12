"""
audio_utils.py
──────────────
Utilities for validating uploaded audio before it is sent to Sunbird STT.

We use the `mutagen` library for duration detection because it is pure-Python,
works on all platforms, and handles every format Sunbird accepts (MP3, WAV,
OGG, M4A, AAC) without requiring ffprobe or any native binaries.
"""

from __future__ import annotations

import io
import logging
import os

import mutagen

from .constants import (
    ACCEPTED_AUDIO_EXTENSIONS,
    ACCEPTED_AUDIO_MIME_TYPES,
    MAX_AUDIO_DURATION_SECONDS,
    MAX_AUDIO_SIZE_BYTES,
)
from .exceptions import AudioTooLongError, UnsupportedFileTypeError, ValidationError

logger = logging.getLogger(__name__)


def validate_audio(
    data: bytes,
    filename: str,
    content_type: str,
) -> None:
    """
    Run all audio validations in order. Raises a typed exception on the first
    failure so the caller gets one clear error message.

    Checks (in order):
      1. File size ≤ 100 MB
      2. Extension is in the accepted set
      3. MIME type is in the accepted set
      4. Duration ≤ 5 minutes (app-level limit)
    """
    # 1. Size
    size = len(data)
    if size > MAX_AUDIO_SIZE_BYTES:
        raise ValidationError(
            f"File is {size / 1_048_576:.1f} MB. Maximum allowed size is 100 MB."
        )

    # 2. Extension
    _, ext = os.path.splitext(filename.lower())
    if ext not in ACCEPTED_AUDIO_EXTENSIONS:
        raise UnsupportedFileTypeError(ext or "(no extension)")

    # 3. MIME type (browsers often send "application/octet-stream" for audio –
    #    we accept that and rely on extension + mutagen for real validation)
    normalised_mime = content_type.split(";")[0].strip().lower()
    if normalised_mime not in ACCEPTED_AUDIO_MIME_TYPES and normalised_mime != "application/octet-stream":
        raise UnsupportedFileTypeError(normalised_mime)

    # 4. Duration via mutagen
    duration = _get_duration_seconds(data, filename)
    if duration is None:
        raise ValidationError(
            "Could not determine audio duration. Please upload a valid mp3, wav, ogg, m4a, or aac file (max 5 minutes)."
        )
    if duration > MAX_AUDIO_DURATION_SECONDS:
        raise AudioTooLongError(duration)

    logger.debug(
        "Audio validated: %s, %.1f s, %d bytes", filename, duration or 0.0, size
    )


def _get_duration_seconds(data: bytes, filename: str) -> float | None:
    """
    Return the audio duration in seconds, or None if mutagen cannot parse it.
    We never reject a file solely because mutagen failed – Sunbird will handle
    any truly invalid audio and return its own error.
    """
    try:
        audio = mutagen.File(io.BytesIO(data), filename=filename)
        if audio is not None and audio.info is not None:
            return float(audio.info.length)
    except Exception as exc:  # noqa: BLE001
        logger.warning("mutagen could not parse '%s': %s", filename, exc)
    return None