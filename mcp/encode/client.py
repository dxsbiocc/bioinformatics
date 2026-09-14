"""Small ENCODE Portal REST client."""

from __future__ import annotations

import json
import os
import time
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx

from .constants import DEFAULT_TOOL_NAME, ENCODE_BASE_URL, JsonObject
from .errors import EncodeError


@dataclass
class EncodeConfig:
    base_url: str = ENCODE_BASE_URL
    contact: str | None = None
    tool: str = DEFAULT_TOOL_NAME
    timeout_seconds: float = 30.0
    max_retries: int = 2
    retry_base_seconds: float = 0.5

    @classmethod
    def from_env(cls) -> EncodeConfig:
        return cls(
            base_url=os.environ.get("ENCODE_BASE_URL", ENCODE_BASE_URL),
            contact=os.environ.get("ENCODE_CONTACT")
            or os.environ.get("EBI_CONTACT")
            or os.environ.get("NCBI_EMAIL")
            or os.environ.get("UNIPROT_CONTACT"),
            tool=os.environ.get("ENCODE_TOOL", DEFAULT_TOOL_NAME),
        )


class EncodeClient:
    """REST client with conservative request pacing."""

    def __init__(
        self,
        config: EncodeConfig | None = None,
        *,
        opener: Callable[[httpx.Request, float], str] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config or EncodeConfig.from_env()
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

    def request_json_with_headers(self, endpoint: str, params: JsonObject | None = None) -> tuple[Any, dict[str, str]]:
        params = {"format": "json", **(params or {})}
        return self._open_json(self.build_url(endpoint, params), endpoint)

    def build_url(self, endpoint: str, params: JsonObject | None = None) -> str:
        endpoint = endpoint.lstrip("/")
        url = f"{self.config.base_url.rstrip('/')}/{endpoint}"
        if not params:
            return url
        encoded = urllib.parse.urlencode(params, doseq=True)
        return f"{url}?{encoded}"

    def browser_url(self, endpoint: str) -> str:
        return f"{self.config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

    def absolute_url(self, path_or_url: str) -> str:
        if path_or_url.startswith(("http://", "https://")):
            return path_or_url
        return f"{self.config.base_url.rstrip('/')}/{path_or_url.lstrip('/')}"

    def _open_json(self, url: str, label: str) -> tuple[Any, dict[str, str]]:
        self._throttle()
        text, response_headers = self._open_url(url, label, accept="application/json")
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise EncodeError(f"ENCODE {label} returned invalid JSON") from exc
        return payload, response_headers

    def _open_url(self, url: str, label: str, *, accept: str) -> tuple[str, dict[str, str]]:
        request = httpx.Request("GET", url, headers={"Accept": accept, "User-Agent": self._user_agent()})
        try:
            if self._opener is not None:
                return self._opener(request, self.config.timeout_seconds), {}
            for attempt in range(self.config.max_retries + 1):
                try:
                    response = self._client.send(request)
                    response.raise_for_status()
                    response_headers = {key.lower(): value for key, value in response.headers.items()}
                    return response.read().decode("utf-8", errors="replace"), response_headers
                except httpx.RequestError:
                    if attempt >= self.config.max_retries:
                        raise
                    self._sleep(self.config.retry_base_seconds * (attempt + 1))
            raise EncodeError(f"Could not reach ENCODE {label}")
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text
            raise EncodeError(f"ENCODE {label} returned HTTP {exc.response.status_code}: {detail[:500]}") from exc
        except httpx.RequestError as exc:
            raise EncodeError(f"Could not reach ENCODE {label}: {exc}") from exc

    def _throttle(self) -> None:
        minimum_interval = 1.0 / self.requests_per_second
        elapsed = self._monotonic() - self._last_request_at
        if elapsed < minimum_interval:
            self._sleep(minimum_interval - elapsed)
        self._last_request_at = self._monotonic()

    def _user_agent(self) -> str:
        if self.config.contact:
            return f"{self.config.tool}/0.1 ({self.config.contact})"
        return f"{self.config.tool}/0.1"

