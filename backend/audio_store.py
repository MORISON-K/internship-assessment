from __future__ import annotations

import time
import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class AudioItem:
    content: bytes
    content_type: str
    expires_at: float


class AudioStore:
    """Tiny in-memory TTL store for generated audio.

    Note: This is intentionally simple for an assessment/demo. It will not work
    across multiple workers/processes.
    """

    def __init__(self, *, ttl_seconds: float = 15 * 60, max_items: int = 128) -> None:
        self._ttl_seconds = float(ttl_seconds)
        self._max_items = int(max_items)
        self._items: dict[str, AudioItem] = {}

    def put(self, content: bytes, content_type: str) -> str:
        self._purge_expired()
        if len(self._items) >= self._max_items:
            # Drop oldest item to make room (simple heuristic).
            oldest_key = min(self._items, key=lambda k: self._items[k].expires_at)
            self._items.pop(oldest_key, None)

        audio_id = uuid.uuid4().hex
        expires_at = time.time() + self._ttl_seconds
        self._items[audio_id] = AudioItem(
            content=content,
            content_type=content_type,
            expires_at=expires_at,
        )
        return audio_id

    def get(self, audio_id: str) -> AudioItem | None:
        self._purge_expired()
        return self._items.get(audio_id)

    def _purge_expired(self) -> None:
        now = time.time()
        expired = [k for k, v in self._items.items() if v.expires_at <= now]
        for k in expired:
            self._items.pop(k, None)
