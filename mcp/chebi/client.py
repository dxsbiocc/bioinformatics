"""Small ChEBI REST client for public EBI endpoints."""

from __future__ import annotations

import json
import os
import time
import urllib.parse
from dataclasses import dataclass
from typing import Any, Callable

import httpx

from .constants import CHEBI_API_BASE_URL, CHEBI_WEBSITE_BASE_URL, DEFAULT_TOOL_NAME, JsonObject
from .errors import ChebiError


@dataclass
class ChebiConfig:
    api_base_url: str = CHEBI_API_BASE_URL
    website_base_url: str = CHEBI_WEBSITE_BASE_URL
    contact: str | None = None
    tool: str = DEFAULT_TOOL_NAME
    timeout_seconds: float = 30.0
    max_retries: int = 1
    retry_base_seconds: float = 0.5

    @classmethod
    def from_env(cls) -> "ChebiConfig":
        return cls(
            api_base_url=os.environ.get("CHEBI_API_BASE_URL", CHEBI_API_BASE_URL),
            website_base_url=os.environ.get("CHEBI_WEBSITE_BASE_URL", CHEBI_WEBSITE_BASE_URL),
            contact=os.environ.get("CHEBI_CONTACT") or os.environ.get("NCBI_EMAIL") or os.environ.get("ENTREZ_EMAIL"),
            tool=os.environ.get("CHEBI_TOOL", DEFAULT_TOOL_NAME),
        )


class ChebiClient:
    """HTTP client with light request pacing for ChEBI public JSON APIs."""

    def __init__(
        self,
        config: ChebiConfig | None = None,
        *,
        opener: Callable[[httpx.Request, float], str | tuple[str, dict[str, str]]] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config or ChebiConfig.from_env()
        self._opener = opener
        self._sleep = sleep
        self._monotonic = monotonic
        self._last_request_at = 0.0
        self._http: httpx.Client | None = None

    @property
    def _client(self) -> httpx.Client:
        if self._http is None:
            self._http = httpx.Client(
                http2=True,
                timeout=httpx.Timeout(self.config.timeout_seconds),
            )
        return self._http

    def close(self) -> None:
        if self._http is not None:
            self._http.close()
            self._http = None

    @property
    def requests_per_second(self) -> int:
        return 3

    def request_json_with_headers(self, endpoint: str, params: JsonObject | None = None) -> tuple[Any, dict[str, str], str]:
        query = params or {}
        url = self._build_url(endpoint, query)
        payload, headers = self._open_json(url, endpoint)
        return payload, headers, url

    def _open_json(self, url: str, label: str) -> tuple[Any, dict[str, str]]:
        self._throttle()
        text, headers = self._open_url(url, label, accept="application/json")
        if not text.strip():
            return {}, headers
        try:
            return json.loads(text), headers
        except json.JSONDecodeError as exc:
            raise ChebiError(f"ChEBI {label} returned invalid JSON") from exc

    def _build_url(self, endpoint: str, params: JsonObject) -> str:
        url = f"{self.config.api_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        if params:
            return f"{url}?{urllib.parse.urlencode(params, doseq=True)}"
        return url

    def _open_url(self, url: str, label: str, *, accept: str) -> tuple[str, dict[str, str]]:
        request = httpx.Request(
            "GET",
            url,
            headers={
                "Accept": accept,
                "User-Agent": self._user_agent(),
            },
        )
        try:
            if self._opener is not None:
                opened = self._opener(request, self.config.timeout_seconds)
                if isinstance(opened, tuple):
                    return opened
                return opened, {}
            for attempt in range(self.config.max_retries + 1):
                try:
                    response = self._client.send(request)
                    response.raise_for_status()
                    headers = {key.lower(): value for key, value in response.headers.items()}
                    return response.read().decode("utf-8", errors="replace"), headers
                except httpx.RequestError:
                    if attempt >= self.config.max_retries:
                        raise
                    self._sleep(self.config.retry_base_seconds * (attempt + 1))
            raise ChebiError(f"Could not reach ChEBI {label}")
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text
            raise ChebiError(f"ChEBI {label} returned HTTP {exc.response.status_code}: {detail[:500]}") from exc
        except httpx.RequestError as exc:
            raise ChebiError(f"Could not reach ChEBI {label}: {exc}") from exc

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
