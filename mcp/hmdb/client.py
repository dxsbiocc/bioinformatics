"""Small HMDB REST client for the unearth search endpoint."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from .constants import DEFAULT_TOOL_NAME, HMDB_BASE_URL, SEARCH_PATH, JsonObject
from .errors import HmdbError


@dataclass
class HmdbConfig:
    base_url: str = HMDB_BASE_URL
    contact: str | None = None
    tool: str = DEFAULT_TOOL_NAME
    timeout_seconds: float = 30.0
    max_retries: int = 1
    retry_base_seconds: float = 0.5

    @classmethod
    def from_env(cls) -> "HmdbConfig":
        return cls(
            base_url=os.environ.get("HMDB_BASE_URL", HMDB_BASE_URL),
            contact=os.environ.get("HMDB_CONTACT") or os.environ.get("NCBI_EMAIL") or os.environ.get("ENTREZ_EMAIL"),
            tool=os.environ.get("HMDB_TOOL", DEFAULT_TOOL_NAME),
        )


class HmdbClient:
    """HTTP client with conservative request pacing and challenge detection."""

    def __init__(
        self,
        config: HmdbConfig | None = None,
        *,
        opener: Callable[[urllib.request.Request, float], str | tuple[str, dict[str, str]]] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config or HmdbConfig.from_env()
        self._opener = opener
        self._sleep = sleep
        self._monotonic = monotonic
        self._last_request_at = 0.0

    @property
    def requests_per_second(self) -> int:
        return 1

    def search_json_with_headers(self, query: str, category: str, max_results: int) -> tuple[Any, dict[str, str], str]:
        params: JsonObject = {"query": query, "category": category, "format": "json", "per_page": max_results}
        url = self._build_url(SEARCH_PATH, params)
        payload, headers = self._open_json(url, f"{SEARCH_PATH}:{category}")
        return payload, headers, url

    def _open_json(self, url: str, label: str) -> tuple[Any, dict[str, str]]:
        self._throttle()
        text, headers = self._open_url(url, label, accept="application/json")
        if not text.strip():
            return {}, headers
        try:
            return json.loads(text), headers
        except json.JSONDecodeError as exc:
            if headers.get("cf-mitigated") == "challenge" or "cloudflare" in text[:500].lower():
                raise HmdbError(
                    "HMDB returned a Cloudflare challenge instead of JSON. "
                    "The MCP uses HMDB's documented unearth endpoint, but this runtime cannot pass the browser challenge."
                ) from exc
            raise HmdbError(f"HMDB {label} returned invalid JSON") from exc

    def _build_url(self, endpoint: str, params: JsonObject) -> str:
        url = f"{self.config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        if params:
            return f"{url}?{urllib.parse.urlencode(params, doseq=True)}"
        return url

    def _open_url(self, url: str, label: str, *, accept: str) -> tuple[str, dict[str, str]]:
        request = urllib.request.Request(
            url,
            headers={
                "Accept": accept,
                "User-Agent": self._user_agent(),
            },
            method="GET",
        )
        try:
            if self._opener is not None:
                opened = self._opener(request, self.config.timeout_seconds)
                if isinstance(opened, tuple):
                    return opened
                return opened, {}
            for attempt in range(self.config.max_retries + 1):
                try:
                    with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                        headers = {key.lower(): value for key, value in response.headers.items()}
                        return response.read().decode("utf-8", errors="replace"), headers
                except urllib.error.URLError:
                    if attempt >= self.config.max_retries:
                        raise
                    self._sleep(self.config.retry_base_seconds * (attempt + 1))
            raise HmdbError(f"Could not reach HMDB {label}")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.headers.get("cf-mitigated") == "challenge" or "cloudflare" in detail[:500].lower():
                raise HmdbError(
                    "HMDB returned HTTP 403 Cloudflare challenge. "
                    "Try the same HMDB URL in a browser, or use another runtime/network that HMDB permits."
                ) from exc
            raise HmdbError(f"HMDB {label} returned HTTP {exc.code}: {detail[:500]}") from exc
        except urllib.error.URLError as exc:
            raise HmdbError(f"Could not reach HMDB {label}: {exc}") from exc

    def _throttle(self) -> None:
        minimum_interval = 1.0 / self.requests_per_second
        now = self._monotonic()
        elapsed = now - self._last_request_at
        if elapsed < minimum_interval:
            self._sleep(minimum_interval - elapsed)
        self._last_request_at = self._monotonic()

    def _user_agent(self) -> str:
        if self.config.contact:
            return f"{self.config.tool}/0.1 ({self.config.contact})"
        return f"{self.config.tool}/0.1"

