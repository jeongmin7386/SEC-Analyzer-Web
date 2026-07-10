"""Small JSON file cache used to protect SEC API quota."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import tempfile
import time
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COMPANYFACTS_CACHE_DIR = PROJECT_ROOT / "cache" / "companyfacts"
DEFAULT_TTL_SECONDS = 24 * 60 * 60


@dataclass(frozen=True)
class CacheReadResult:
    payload: dict[str, Any] | None
    hit: bool
    key: str
    path: Path
    age_seconds: float | None
    expires_in_seconds: float | None


class JsonFileCache:
    """TTL based JSON cache with explicit metadata for API responses."""

    def __init__(
        self,
        directory: Path = DEFAULT_COMPANYFACTS_CACHE_DIR,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        self.directory = directory
        self.ttl_seconds = ttl_seconds

    def get(self, key: str) -> CacheReadResult:
        safe_key = cache_key(key)
        path = self.path_for(safe_key)
        if not path.exists():
            return CacheReadResult(None, False, safe_key, path, None, None)

        try:
            age_seconds = time.time() - path.stat().st_mtime
            if age_seconds > self.ttl_seconds:
                return CacheReadResult(
                    None,
                    False,
                    safe_key,
                    path,
                    age_seconds,
                    0.0,
                )

            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return CacheReadResult(None, False, safe_key, path, None, None)

        if not isinstance(payload, dict):
            return CacheReadResult(None, False, safe_key, path, age_seconds, 0.0)

        return CacheReadResult(
            payload,
            True,
            safe_key,
            path,
            age_seconds,
            max(self.ttl_seconds - age_seconds, 0.0),
        )

    def set(self, key: str, payload: dict[str, Any]) -> Path:
        safe_key = cache_key(key)
        path = self.path_for(safe_key)
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
        except OSError:
            fallback_dir = Path(tempfile.gettempdir()) / "sec-stock-analyzer-cache" / self.directory.name
            fallback_dir.mkdir(parents=True, exist_ok=True)
            self.directory = fallback_dir
            path = self.path_for(safe_key)
            path.write_text(
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
        return path

    def invalidate(self, key: str) -> bool:
        path = self.path_for(cache_key(key))
        if not path.exists():
            return False
        path.unlink()
        return True

    def path_for(self, key: str) -> Path:
        return self.directory / f"{cache_key(key)}.json"


def cache_key(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value).strip().upper())
    return cleaned or "UNKNOWN"


def cache_meta(
    *,
    used: bool,
    source: str,
    key: str,
    path: Path | None = None,
    age_seconds: float | None = None,
    expires_in_seconds: float | None = None,
) -> dict[str, Any]:
    return {
        "used": used,
        "source": source,
        "key": key,
        "path": str(path) if path else None,
        "ageSeconds": round(age_seconds, 3) if age_seconds is not None else None,
        "expiresInSeconds": (
            round(expires_in_seconds, 3) if expires_in_seconds is not None else None
        ),
        "checkedAt": datetime.now(timezone.utc).isoformat(),
    }
