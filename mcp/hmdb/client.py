"""Small HMDB REST client for the unearth search endpoint."""

from __future__ import annotations

import json
import os
import time
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from mcp.http_client import Opener, PacedHttpClient

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
    def from_env(cls) -> HmdbConfig:
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
        opener: Opener | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config or HmdbConfig.from_env()
        self._http = PacedHttpClient(
            error_class=HmdbError,
            service_name="HMDB",
            timeout_seconds=self.config.timeout_seconds,
            max_retries=self.config.max_retries,
            retry_base_seconds=self.config.retry_base_seconds,
            requests_per_second=self.requests_per_second,
            opener=opener,
            sleep=sleep,
            monotonic=monotonic,
        )

    def close(self) -> None:
        self._http.close()

    @property
    def requests_per_second(self) -> int:
        return 1

    def search_json_with_headers(self, query: str, category: str, max_results: int) -> tuple[Any, dict[str, str], str]:
        params: JsonObject = {"query": query, "category": category, "format": "json", "per_page": max_results}
        url = self._build_url(SEARCH_PATH, params)
        payload, headers = self._open_json(url, f"{SEARCH_PATH}:{category}")
        return payload, headers, url

    def _open_json(self, url: str, label: str) -> tuple[Any, dict[str, str]]:
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
        headers = {
            "Accept": accept,
            "User-Agent": self._user_agent(),
        }
        try:
            return self._http.send("GET", url, headers, label=label)
        except HmdbError as exc:
            if exc.headers.get("cf-mitigated") == "challenge" or "cloudflare" in exc.response_body[:500].lower():
                raise HmdbError(
                    "HMDB returned HTTP 403 Cloudflare challenge. "
                    "Try the same HMDB URL in a browser, or use another runtime/network that HMDB permits."
                ) from exc
            raise

    def _user_agent(self) -> str:
        if self.config.contact:
            return f"{self.config.tool}/0.1 ({self.config.contact})"
        return f"{self.config.tool}/0.1"
