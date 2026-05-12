"""
Custom exception hierarchy for the Sunbird pipeline.
All exceptions carry a user-facing `detail` string and an HTTP `status_code`
so FastAPI route handlers can re-raise them as HTTPException with zero boilerplate.
"""


class SunbirdBaseError(Exception):
    """Root exception for every error that originates inside this backend."""

    def __init__(self, detail: str, status_code: int = 500) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


# ── Authentication ────────────────────────────────────────────────────────────

class AuthenticationError(SunbirdBaseError):
    """Raised when the Sunbird API token is missing or rejected (HTTP 401)."""

    def __init__(self, detail: str = "Invalid or missing Sunbird API token.") -> None:
        super().__init__(detail, status_code=401)


# ── Validation ────────────────────────────────────────────────────────────────

class ValidationError(SunbirdBaseError):
    """Raised for client-side validation problems (HTTP 422)."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail, status_code=422)


class AudioTooLongError(ValidationError):
    """Audio file exceeds the 5-minute cap enforced by this application."""

    def __init__(self, duration_seconds: float) -> None:
        minutes = duration_seconds / 60
        super().__init__(
            f"Audio is {minutes:.1f} min long. Maximum allowed duration is 5 minutes."
        )


class UnsupportedFileTypeError(ValidationError):
    """MIME type or extension is not accepted."""

    def __init__(self, received: str) -> None:
        super().__init__(
            f"Unsupported file type '{received}'. "
            "Accepted formats: mp3, wav, ogg, m4a, aac."
        )


class UnsupportedLanguageError(ValidationError):
    """Target language code is not in the supported set."""

    def __init__(self, lang: str) -> None:
        super().__init__(
            f"Language '{lang}' is not supported. "
            "Choose from: lug, nyn, teo, lgg, ach."
        )


# ── Upstream API errors ───────────────────────────────────────────────────────

class SunbirdAPIError(SunbirdBaseError):
    """Propagated when the Sunbird REST API returns a non-2xx response."""

    def __init__(self, endpoint: str, status: int, body: str) -> None:
        detail = f"Sunbird API error on '{endpoint}' (HTTP {status}): {body}"
        # Surface 4xx as-is; wrap 5xx as 502 Bad Gateway
        http_code = status if 400 <= status < 500 else 502
        super().__init__(detail, status_code=http_code)
        self.upstream_status = status
        self.endpoint = endpoint


class RateLimitError(SunbirdAPIError):
    """Raised after all retry attempts are exhausted on HTTP 429 / 503."""

    def __init__(self, endpoint: str) -> None:
        # Bypass SunbirdAPIError's constructor – we already know the cause
        SunbirdBaseError.__init__(
            self,
            detail=(
                f"Sunbird rate limit exceeded on '{endpoint}'. "
                "Please wait a moment and try again."
            ),
            status_code=429,
        )
        self.upstream_status = 429
        self.endpoint = endpoint


class TranscriptionError(SunbirdAPIError):
    """STT-specific wrapper so callers can distinguish transcription failures."""


class SummarisationError(SunbirdAPIError):
    """Summarisation-specific wrapper."""


class TranslationError(SunbirdAPIError):
    """Translation-specific wrapper."""


class TTSError(SunbirdAPIError):
    """Text-to-Speech-specific wrapper."""