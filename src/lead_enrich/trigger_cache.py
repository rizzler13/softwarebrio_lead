"""
File-backed cache for trigger event results.

Saves discovered trigger events to disk so re-running the same domains
doesn't burn tokens rediscovering the same fundraise announcement.
Cache entries expire after a configurable TTL (default 7 days).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import structlog

from lead_enrich.models import TriggerEvent

log = structlog.get_logger()

# Default cache location — lives next to output files so it's visible and deletable
_DEFAULT_CACHE_PATH = Path("output") / ".trigger_cache.json"
_DEFAULT_TTL_SECONDS = 7 * 24 * 3600  # 7 days


class TriggerCache:
    """
    Simple JSON-backed cache for trigger event results.

    Cache key is the lowercase domain. Each entry stores the serialized
    TriggerEvent plus a timestamp for TTL expiry.
    """

    def __init__(
        self,
        cache_path: Path = _DEFAULT_CACHE_PATH,
        ttl_seconds: int = _DEFAULT_TTL_SECONDS,
        enabled: bool = True,
    ) -> None:
        self._path = cache_path
        self._ttl = ttl_seconds
        self._enabled = enabled
        self._data: dict[str, dict[str, Any]] = {}

        if enabled:
            self._load()

    def _load(self) -> None:
        """Load cache from disk, silently ignoring corruption."""
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                self._data = raw
        except Exception as exc:
            log.debug("trigger_cache_load_error", error=str(exc))
            self._data = {}

    def _save(self) -> None:
        """Persist cache to disk."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as exc:
            log.debug("trigger_cache_save_error", error=str(exc))

    def get(self, domain: str) -> TriggerEvent | None:
        """
        Retrieve a cached trigger event for a domain.

        Returns None if cache is disabled, no entry exists, or the entry has expired.
        """
        if not self._enabled:
            return None

        key = domain.lower().strip()
        entry = self._data.get(key)
        if not entry:
            return None

        cached_at = entry.get("cached_at", 0)
        if time.time() - cached_at > self._ttl:
            # Expired — remove stale entry
            del self._data[key]
            self._save()
            log.debug("trigger_cache_expired", domain=key)
            return None

        try:
            event_data = entry.get("event")
            if event_data:
                event = TriggerEvent.model_validate(event_data)
                log.info("trigger_cache_hit", domain=key, found=event.found)
                return event
        except Exception as exc:
            log.debug("trigger_cache_parse_error", domain=key, error=str(exc))

        return None

    def put(self, domain: str, event: TriggerEvent) -> None:
        """Store a trigger event result in the cache."""
        if not self._enabled:
            return

        key = domain.lower().strip()
        self._data[key] = {
            "event": event.model_dump(mode="json"),
            "cached_at": time.time(),
        }
        self._save()
        log.debug("trigger_cache_stored", domain=key, found=event.found)

    def clear(self) -> None:
        """Remove all cache entries."""
        self._data = {}
        if self._path.exists():
            try:
                self._path.unlink()
            except Exception:
                pass

    @property
    def size(self) -> int:
        """Number of entries currently in the cache."""
        return len(self._data)
