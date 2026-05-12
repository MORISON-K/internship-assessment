"""
Shared constants, language metadata, and TTS voice mappings.
Single source of truth – imported by sunbird_client, pipeline, models, and routes.
"""

from __future__ import annotations

from dataclasses import dataclass

# ── Sunbird base URL ──────────────────────────────────────────────────────────

SUNBIRD_BASE_URL = "https://api.sunbird.ai"

# ── Audio constraints ─────────────────────────────────────────────────────────

MAX_AUDIO_DURATION_SECONDS: float = 5 * 60  # 5 minutes – app-level limit
MAX_AUDIO_SIZE_BYTES: int = 100 * 1024 * 1024  # 100 MB – Sunbird API limit

ACCEPTED_AUDIO_EXTENSIONS = frozenset(
    {".mp3", ".wav", ".ogg", ".m4a", ".aac"}
)
ACCEPTED_AUDIO_MIME_TYPES = frozenset(
    {
        "audio/mpeg",
        "audio/mp3",
        "audio/wav",
        "audio/x-wav",
        "audio/ogg",
        "audio/mp4",
        "audio/m4a",
        "audio/x-m4a",
        "audio/aac",
        "audio/x-aac",
    }
)

# ── Retry policy (applied to 429 / 503 responses) ────────────────────────────

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds; delay = RETRY_BACKOFF_BASE ** attempt

# ── Supported translation-target languages ────────────────────────────────────


@dataclass(frozen=True)
class Language:
    code: str          # Sunbird language code (also used in prompts)
    name: str          # Human-readable English name
    tts_speaker_id: int | None  # None → TTS not available for this language


# All languages supported for translation + TTS in this app.
LANGUAGES: dict[str, Language] = {
    "lug": Language(code="lug", name="Luganda",     tts_speaker_id=248),
    "nyn": Language(code="nyn", name="Runyankole",  tts_speaker_id=243),
    "teo": Language(code="teo", name="Ateso",       tts_speaker_id=242),
    "lgg": Language(code="lgg", name="Lugbara",     tts_speaker_id=245),
    "ach": Language(code="ach", name="Acholi",      tts_speaker_id=241),
}

SUPPORTED_LANGUAGE_CODES = frozenset(LANGUAGES.keys())

# ── HTTP client timeouts (seconds) ────────────────────────────────────────────

STT_TIMEOUT = 120.0        # audio transcription can be slow
LLM_TIMEOUT = 60.0         # summarise / translate
TTS_TIMEOUT = 60.0         # TTS generation
DEFAULT_TIMEOUT = 30.0