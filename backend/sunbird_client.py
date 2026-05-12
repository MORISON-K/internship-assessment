"""
sunbird_client.py
─────────────────
Thin async wrapper around every Sunbird AI REST endpoint used by this app.

Responsibilities
  • Attach the Bearer token to every request.
  • Implement exponential-backoff retries for 429 / 503 responses.
  • Map upstream HTTP errors to typed exceptions from exceptions.py.
  • Return plain Python dicts / bytes – no business logic lives here.

All network I/O is done through a single shared httpx.AsyncClient that is
created once at application startup (lifespan) and injected via dependency.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from .constants import (
    SUNBIRD_BASE_URL,
    MAX_RETRIES,
    RETRY_BACKOFF_BASE,
    STT_TIMEOUT,
    LLM_TIMEOUT,
    TTS_TIMEOUT,
    LANGUAGES,
)
from .exceptions import (
    AuthenticationError,
    RateLimitError,
    SunbirdAPIError,
    TranscriptionError,
    SummarisationError,
    TranslationError,
    TTSError,
)

logger = logging.getLogger(__name__)


# ── Low-level helpers ─────────────────────────────────────────────────────────


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _post_with_retry(
    client: httpx.AsyncClient,
    url: str,
    *,
    headers: dict[str, str],
    json: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    files: dict[str, Any] | None = None,
    timeout: float,
    error_cls: type[SunbirdAPIError],
) -> dict[str, Any]:
    """
    POST to *url* with automatic exponential-backoff on 429 / 503.
    Raises the appropriate typed exception on unrecoverable errors.
    """
    endpoint = url.replace(SUNBIRD_BASE_URL, "")
    last_exc: Exception | None = None

    for attempt in range(MAX_RETRIES):
        try:
            response = await client.post(
                url,
                headers=headers,
                json=json,
                data=data,
                files=files,
                timeout=timeout,
            )
        except httpx.TimeoutException as exc:
            logger.warning("Timeout on %s (attempt %d/%d)", endpoint, attempt + 1, MAX_RETRIES)
            last_exc = exc
            await asyncio.sleep(RETRY_BACKOFF_BASE ** attempt)
            continue
        except httpx.RequestError as exc:
            logger.error("Network error on %s: %s", endpoint, exc)
            raise SunbirdAPIError(endpoint, 0, str(exc)) from exc

        if response.status_code == 200:
            return response.json()

        if response.status_code == 401:
            raise AuthenticationError()

        if response.status_code in (429, 503):
            wait = RETRY_BACKOFF_BASE ** attempt
            logger.warning(
                "Rate-limited on %s (attempt %d/%d). Retrying in %ds.",
                endpoint, attempt + 1, MAX_RETRIES, wait,
            )
            last_exc = RateLimitError(endpoint)
            await asyncio.sleep(wait)
            continue

        # Non-retryable 4xx / 5xx
        body = response.text
        logger.error("Upstream error %s on %s: %s", response.status_code, endpoint, body)
        raise error_cls(endpoint, response.status_code, body)

    # All retries exhausted
    if isinstance(last_exc, RateLimitError):
        raise last_exc
    raise SunbirdAPIError(endpoint, 0, "All retry attempts timed out.")


# ── Public client class ───────────────────────────────────────────────────────


class SunbirdClient:
    """
    Async client for the Sunbird AI API.

    Usage (FastAPI lifespan pattern):
        client = SunbirdClient(token=settings.sunbird_api_token)
        await client.aopen()
        ...
        await client.aclose()

    Or as an async context manager:
        async with SunbirdClient(token=...) as client:
            transcript = await client.transcribe(audio_bytes, filename)
    """

    def __init__(self, token: str) -> None:
        if not token:
            raise AuthenticationError("SUNBIRD_API_TOKEN is not set.")
        self._token = token
        self._client: httpx.AsyncClient | None = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def aopen(self) -> None:
        self._client = httpx.AsyncClient(base_url=SUNBIRD_BASE_URL)

    async def aclose(self) -> None:
        if self._client:
            await self._client.aclose()

    async def __aenter__(self) -> "SunbirdClient":
        await self.aopen()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.aclose()

    @property
    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("SunbirdClient not opened. Call aopen() first.")
        return self._client

    # ── STT ───────────────────────────────────────────────────────────────────

    async def transcribe(
        self,
        audio_bytes: bytes,
        filename: str,
        content_type: str,
    ) -> dict[str, Any]:
        """
        POST audio to /tasks/stt.

        Returns the full ``output`` dict::

            {"text": "...", "language": "eng"}
        """
        logger.info("STT request: %s (%d bytes)", filename, len(audio_bytes))
        files = {"audio": (filename, audio_bytes, content_type)}
        result = await _post_with_retry(
            self._http,
            f"{SUNBIRD_BASE_URL}/tasks/stt",
            headers=_auth_headers(self._token),
            files=files,
            timeout=STT_TIMEOUT,
            error_cls=TranscriptionError,
        )
        # Sunbird responses have appeared in a few shapes across docs/OpenAPI.
        # Normalize to the internal shape expected by pipeline.py:
        #   {"text": "...", "language": "..."}
        output = result.get("output")

        text: str = ""
        language: str | None = None

        if isinstance(output, dict):
            text = (
                output.get("text")
                or output.get("audio_transcription")
                or output.get("transcript")
                or ""
            )
            language = (
                output.get("language")
                or output.get("detected_language")
                or output.get("lang")
            )
        else:
            # OpenAPI variants may return fields at the top-level.
            text = (
                result.get("audio_transcription")
                or result.get("text")
                or result.get("transcript")
                or ""
            )
            language = (
                result.get("language")
                or result.get("detected_language")
                or result.get("lang")
            )

        text = str(text).strip()
        language = str(language).strip() if language is not None else None
        logger.info("STT complete. Detected language: %s", language)
        return {"text": text, "language": language}

    # ── Summarise ─────────────────────────────────────────────────────────────

    async def summarise(self, text: str) -> str:
        """
        Ask Sunflower to produce a concise English summary of *text*.
        Returns the summary string.
        """
        logger.info("Summarisation request (%d chars)", len(text))
        prompt = (
            "Please provide a clear and concise summary of the following text. "
            "Keep the summary to 3-5 sentences and write only in English.\n\n"
            f"Text:\n{text}"
        )
        # Prefer the OpenAPI shape (x-www-form-urlencoded); fall back to JSON if
        # the server rejects form encoding.
        try:
            result = await _post_with_retry(
                self._http,
                f"{SUNBIRD_BASE_URL}/tasks/sunflower_simple",
                headers=_auth_headers(self._token),
                data={"instruction": prompt, "model_type": "qwen", "temperature": 0.3},
                timeout=LLM_TIMEOUT,
                error_cls=SummarisationError,
            )
        except SummarisationError as exc:
            if getattr(exc, "upstream_status", None) in (415, 422):
                result = await _post_with_retry(
                    self._http,
                    f"{SUNBIRD_BASE_URL}/tasks/sunflower_simple",
                    headers={**_auth_headers(self._token), "Content-Type": "application/json"},
                    json={"instruction": prompt, "model_type": "qwen", "temperature": 0.3},
                    timeout=LLM_TIMEOUT,
                    error_cls=SummarisationError,
                )
            else:
                raise
        summary = self._extract_llm_text(result)
        if not summary.strip():
            raise SummarisationError(
                "/tasks/sunflower_simple",
                502,
                "Sunflower summarisation returned an empty response.",
            )
        logger.info("Summarisation complete (%d chars)", len(summary))
        return summary

    # ── Translate ─────────────────────────────────────────────────────────────

    async def translate(self, text: str, target_language_code: str) -> str:
        """
        Translate *text* into *target_language_code* using Sunflower Chat inference.
        Returns the translated string.
        """
        lang = LANGUAGES[target_language_code]
        logger.info("Translation request → %s (%s)", lang.name, lang.code)

        system_prompt = (
            f"You are an expert translator. "
            f"Your only task is to translate the provided text into {lang.name}. "
            f"Output only the translated text with no explanation, preamble, or notes."
        )
        user_prompt = f"Translate the following text into {lang.name}:\n\n{text}"

        result = await _post_with_retry(
            self._http,
            f"{SUNBIRD_BASE_URL}/tasks/sunflower_inference",
            headers={**_auth_headers(self._token), "Content-Type": "application/json"},
            json={
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
            },
            timeout=LLM_TIMEOUT,
            error_cls=TranslationError,
        )
        translated = self._extract_chat_text(result)
        if not translated.strip():
            raise TranslationError(
                "/tasks/sunflower_inference",
                502,
                "Sunflower translation returned an empty response.",
            )
        logger.info("Translation complete (%d chars)", len(translated))
        return translated

    # ── TTS ───────────────────────────────────────────────────────────────────

    async def synthesise_speech(
        self, text: str, target_language_code: str
    ) -> str:
        """
        Convert *text* to speech using the TTS speaker for *target_language_code*.
        Returns the signed audio URL.
        """
        lang = LANGUAGES[target_language_code]
        if lang.tts_speaker_id is None:
            raise TTSError(
                "/tasks/tts",
                422,
                f"TTS is not available for language '{lang.name}'.",
            )

        logger.info(
            "TTS request: speaker_id=%d, lang=%s (%d chars)",
            lang.tts_speaker_id, lang.code, len(text),
        )
        result = await _post_with_retry(
            self._http,
            f"{SUNBIRD_BASE_URL}/tasks/tts",
            headers={**_auth_headers(self._token), "Content-Type": "application/json"},
            json={"text": text, "speaker_id": lang.tts_speaker_id},
            timeout=TTS_TIMEOUT,
            error_cls=TTSError,
        )
        output = result.get("output")
        audio_url: str | None = None
        if isinstance(output, dict):
            audio_url = output.get("audio_url")
        if not audio_url:
            audio_url = result.get("audio_url")
        if not audio_url or not str(audio_url).strip():
            raise TTSError(
                "/tasks/tts",
                502,
                "Unexpected TTS response (missing audio_url).",
            )
        logger.info("TTS complete. Audio URL received.")
        return str(audio_url).strip()

    async def download_audio(self, audio_url: str) -> tuple[bytes, str]:
        """Download generated audio bytes from a signed URL returned by TTS."""
        try:
            response = await self._http.get(
                audio_url,
                follow_redirects=True,
                timeout=TTS_TIMEOUT,
            )
        except httpx.RequestError as exc:
            raise TTSError(
                "/tasks/tts",
                502,
                f"Failed to download generated audio: {exc}",
            ) from exc

        if response.status_code != 200:
            raise TTSError(
                "/tasks/tts",
                502,
                f"Failed to download generated audio (HTTP {response.status_code}).",
            )

        content_type = (response.headers.get("content-type") or "audio/mpeg").split(";")[
            0
        ].strip()
        if not content_type:
            content_type = "audio/mpeg"
        return response.content, content_type

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _extract_llm_text(result: dict[str, Any]) -> str:
        """Extract text from a /tasks/sunflower_simple response."""
        # OpenAPI shape: {"response": "..."}
        response = result.get("response")
        if isinstance(response, str):
            return response.strip()

        # Guide/older shape: {"output": {"text": "..."}} or just a string
        output = result.get("output", result)
        if isinstance(output, str):
            return output.strip()
        if isinstance(output, dict):
            return (output.get("text") or output.get("content") or "").strip()
        return str(output).strip()

    @staticmethod
    def _extract_chat_text(result: dict[str, Any]) -> str:
        """Extract text from a /tasks/sunflower_inference response."""
        # OpenAPI shape: {"content": "..."}
        content = result.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()

        # Guide/older shape: {"output": {"content": "..."}}
        output = result.get("output", {})
        if isinstance(output, dict):
            return (output.get("content") or output.get("text") or "").strip()
        return str(output).strip()