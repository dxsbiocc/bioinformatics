"""Small RCSB PDB API client."""

from __future__ import annotations

import json
import os
import time
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass

import httpx

from .constants import (
    DEFAULT_TOOL_NAME,
    RCSB_DATA_API_BASE_URL,
    RCSB_FILES_BASE_URL,
    RCSB_SEARCH_API_BASE_URL,
    RCSB_WEBSITE_BASE_URL,
    JsonObject,
)
from .errors import RcsbError


@dataclass
class RcsbConfig:
    data_base_url: str = RCSB_DATA_API_BASE_URL
    search_base_url: str = RCSB_SEARCH_API_BASE_URL
    website_base_url: str = RCSB_WEBSITE_BASE_URL
    files_base_url: str = RCSB_FILES_BASE_URL
    contact: str | None = None
    tool: str = DEFAULT_TOOL_NAME
    timeout_seconds: float = 30.0
    max_retries: int = 2
    retry_base_seconds: float = 0.5

    @classmethod
    def from_env(cls) -> RcsbConfig:
        return cls(
            data_base_url=os.environ.get("RCSB_DATA_BASE_URL", RCSB_DATA_API_BASE_URL),
            search_base_url=os.environ.get("RCSB_SEARCH_BASE_URL", RCSB_SEARCH_API_BASE_URL),
            website_base_url=os.environ.get("RCSB_WEBSITE_BASE_URL", RCSB_WEBSITE_BASE_URL),
            files_base_url=os.environ.get("RCSB_FILES_BASE_URL", RCSB_FILES_BASE_URL),
            contact=os.environ.get("RCSB_CONTACT")
            or os.environ.get("UNIPROT_CONTACT")
            or os.environ.get("NCBI_EMAIL")
            or os.environ.get("ENTREZ_EMAIL"),
            tool=os.environ.get("RCSB_TOOL", DEFAULT_TOOL_NAME),
        )


class RcsbClient:
    """Small REST client with conservative request pacing."""

    def __init__(
        self,
        config: RcsbConfig | None = None,
        *,
        opener: Callable[[httpx.Request, float], str] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config or RcsbConfig.from_env()
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
        return 2

    def request_data_json_with_headers(
        self,
        endpoint: str,
        params: JsonObject | None = None,
    ) -> tuple[JsonObject, dict[str, str]]:
        return self.request_json_with_headers(
            self._build_url(self.config.data_base_url, endpoint, params or {}),
            endpoint,
        )

    def request_search_json_with_headers(
        self,
        endpoint: str,
        payload: JsonObject,
    ) -> tuple[JsonObject, dict[str, str]]:
        endpoint = endpoint.lstrip("/")
        url = f"{self.config.search_base_url.rstrip('/')}/{endpoint}"
        body = json.dumps(payload).encode("utf-8")
        return self._open_json(
            url,
            endpoint,
            method="POST",
            body=body,
            headers={"Content-Type": "application/json"},
        )

    def request_text_with_headers(
        self,
        url: str,
        *,
        label: str,
        accept: str = "text/plain",
    ) -> tuple[str, dict[str, str]]:
        self._throttle()
        return self._open_url(url, label, accept=accept)

    def request_json_with_headers(
        self,
        url: str,
        label: str,
    ) -> tuple[JsonObject, dict[str, str]]:
        return self._open_json(url, label, method="GET", body=None, headers={})

    def _open_json(
        self,
        url: str,
        label: str,
        *,
        method: str,
        body: bytes | None,
        headers: dict[str, str],
    ) -> tuple[JsonObject, dict[str, str]]:
        self._throttle()
        text, response_headers = self._open_url(
            url,
            label,
            accept="application/json",
            method=method,
            body=body,
            extra_headers=headers,
        )
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RcsbError(f"RCSB {label} returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise RcsbError(f"RCSB {label} returned non-object JSON")
        return payload, response_headers

    def _build_url(self, base_url: str, endpoint: str, params: JsonObject) -> str:
        endpoint = endpoint.lstrip("/")
        url = f"{base_url.rstrip('/')}/{endpoint}"
        if not params:
            return url
        encoded = urllib.parse.urlencode(params, doseq=True)
        return f"{url}?{encoded}"

    def _open_url(
        self,
        url: str,
        label: str,
        *,
        accept: str,
        method: str = "GET",
        body: bytes | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> tuple[str, dict[str, str]]:
        headers = {
            "Accept": accept,
            "User-Agent": self._user_agent(),
            **(extra_headers or {}),
        }
        request = httpx.Request(method, url, headers=headers, content=body)
        try:
            if self._opener is not None:
                return self._opener(request, self.config.timeout_seconds), {}
            for attempt in range(self.config.max_retries + 1):
                try:
                    response = self._client.send(request)
                    response.raise_for_status()
                    response_headers = {
                        key.lower(): value
                        for key, value in response.headers.items()
                    }
                    text = response.read().decode("utf-8", errors="replace")
                    return text, response_headers
                except httpx.RequestError:
                    if attempt >= self.config.max_retries:
                        raise
                    self._sleep(self.config.retry_base_seconds * (attempt + 1))
            raise RcsbError(f"Could not reach RCSB {label}")
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text
            raise RcsbError(
                f"RCSB {label} returned HTTP {exc.response.status_code}: {detail[:500]}"
            ) from exc
        except httpx.RequestError as exc:
            raise RcsbError(f"Could not reach RCSB {label}: {exc}") from exc

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

