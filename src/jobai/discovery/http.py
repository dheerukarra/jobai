"""Polite HTTP client: per-host spacing, retry on 429/5xx only, no cookies (new WP1a file)."""

import hashlib
import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

from jobai.discovery.models import FetchError

USER_AGENT = "JobAi/0.1 (personal use)"
TIMEOUT_S = 20.0
MIN_INTERVAL_S = 1.0
MAX_ATTEMPTS = 3
MAX_RETRY_AFTER_S = 60.0


class HttpStatusError(FetchError):
    def __init__(self, status: int, url: str) -> None:
        super().__init__(f"HTTP {status} for {url}")
        self.status = status


class PoliteClient:
    """Sequential client. One request at a time, >= min_interval between requests per host."""

    def __init__(
        self,
        *,
        transport: httpx.BaseTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        min_interval: float = MIN_INTERVAL_S,
        cache_dir: Path | None = None,
    ) -> None:
        self._client = httpx.Client(
            transport=transport,
            timeout=TIMEOUT_S,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            follow_redirects=False,
        )
        self._clock = clock
        self._sleep = sleep
        self._min_interval = min_interval
        self._last: dict[str, float] = {}
        self.request_count = 0
        self._cache_dir = cache_dir

    def close(self) -> None:
        self._client.close()

    def _wait_turn(self, host: str) -> None:
        last = self._last.get(host)
        if last is not None:
            gap = self._min_interval - (self._clock() - last)
            if gap > 0:
                self._sleep(gap)
        self._last[host] = self._clock()

    @staticmethod
    def _retry_after(resp: httpx.Response) -> float | None:
        raw = resp.headers.get("Retry-After")
        if raw is None:
            return None
        try:
            return min(max(float(raw), 0.0), MAX_RETRY_AFTER_S)
        except ValueError:
            return None

    def _cache_path(self, url: str) -> Path | None:
        if self._cache_dir is None:
            return None
        return self._cache_dir / (hashlib.sha256(url.encode()).hexdigest()[:40] + ".json")

    def get_json(self, url: str, *, cache_ttl: float | None = None) -> Any:
        """GET JSON. With cache_ttl (seconds) and a cache_dir, reuse a fresh on-disk copy."""
        path = self._cache_path(url) if cache_ttl else None
        if path is not None and path.is_file() and time.time() - path.stat().st_mtime < (
            cache_ttl or 0
        ):
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                pass
        data = self._fetch_json(url)
        if path is not None:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(data), encoding="utf-8")
            except OSError:
                pass
        return data

    def _fetch_json(self, url: str) -> Any:
        host = urlsplit(url).hostname or ""
        for attempt in range(MAX_ATTEMPTS):
            self._wait_turn(host)
            self.request_count += 1
            try:
                resp = self._client.get(url)
            except httpx.TimeoutException as e:
                raise FetchError(f"timeout fetching {url}") from e
            except httpx.HTTPError as e:
                raise FetchError(f"network error fetching {url}: {type(e).__name__}") from e
            status = resp.status_code
            if status == 429 or status >= 500:
                if attempt == MAX_ATTEMPTS - 1:
                    raise HttpStatusError(status, url)
                backoff = self._retry_after(resp)
                self._sleep(backoff if backoff is not None else 2.0 * (2**attempt))
                continue
            if status >= 300:
                raise HttpStatusError(status, url)
            try:
                return resp.json()
            except ValueError as e:
                raise FetchError(f"invalid JSON from {url}") from e
        raise FetchError(f"exhausted retries for {url}")  # pragma: no cover
