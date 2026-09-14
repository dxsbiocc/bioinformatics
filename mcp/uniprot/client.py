"""Small UniProt REST client."""

from __future__ import annotations

import json
import os
import time
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass

import httpx

from .constants import DEFAULT_TOOL_NAME, UNIPROT_REST_BASE_URL, JsonObject
from .errors import UniProtError


@dataclass
class UniProtConfig:
    base_url: str = UNIPROT_REST_BASE_URL
    contact: str | None = None
    tool: str = DEFAULT_TOOL_NAME
    timeout_seconds: float = 30.0
    max_retries: int = 2
    retry_base_seconds: float = 0.5

    @classmethod
    def from_env(cls) -> UniProtConfig:
        return cls(
            base_url=os.environ.get("UNIPROT_BASE_URL", UNIPROT_REST_BASE_URL),
            contact=os.environ.get("UNIPROT_CONTACT")
            or os.environ.get("NCBI_EMAIL")
            or os.environ.get("ENTREZ_EMAIL"),
            tool=os.environ.get("UNIPROT_TOOL", DEFAULT_TOOL_NAME),
        )


class UniProtClient:
    """Small REST client with conservative request pacing."""

    def __init__(
        self,
        config: UniProtConfig | None = None,
        *,
        opener: Callable[[httpx.Request, float], str] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config or UniProtConfig.from_env()
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

    def request_json(self, endpoint: str, params: JsonObject) -> JsonObject:
        text = self.request_text(endpoint, params, accept="application/json")
        return self._parse_json(endpoint, text)

    def request_json_with_headers(
        self,
        endpoint: str,
        params: JsonObject,
    ) -> tuple[JsonObject, dict[str, str]]:
        text, headers = self.request_text_with_headers(
            endpoint,
            params,
            accept="application/json",
        )
        return self._parse_json(endpoint, text), headers

    def _parse_json(self, endpoint: str, text: str) -> JsonObject:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise UniProtError(f"UniProt {endpoint} returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise UniProtError(f"UniProt {endpoint} returned non-object JSON")
        return payload

    def request_text(
        self,
        endpoint: str,
        params: JsonObject | None = None,
        *,
        accept: str = "text/plain",
    ) -> str:
        text, _headers = self.request_text_with_headers(endpoint, params, accept=accept)
        return text

    def request_text_with_headers(
        self,
        endpoint: str,
        params: JsonObject | None = None,
        *,
        accept: str = "text/plain",
    ) -> tuple[str, dict[str, str]]:
        self._throttle()
        url = self._build_url(endpoint, params or {})
        return self._open_url(url, endpoint, accept)

    def _build_url(self, endpoint: str, params: JsonObject) -> str:
        endpoint = endpoint.lstrip("/")
        url = f"{self.config.base_url.rstrip('/')}/{endpoint}"
        if not params:
            return url
        encoded = urllib.parse.urlencode(params, doseq=True)
        return f"{url}?{encoded}"

    def _open_url(self, url: str, label: str, accept: str) -> tuple[str, dict[str, str]]:
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
                return self._opener(request, self.config.timeout_seconds), {}
            for attempt in range(self.config.max_retries + 1):
                try:
                    response = self._client.send(request)
                    response.raise_for_status()
                    headers = {
                        key.lower(): value
                        for key, value in response.headers.items()
                    }
                    text = response.read().decode("utf-8", errors="replace")
                    return text, headers
                except httpx.RequestError:
                    if attempt >= self.config.max_retries:
                        raise
                    self._sleep(self.config.retry_base_seconds * (attempt + 1))
            raise UniProtError(f"Could not reach UniProt {label}")
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text
            raise UniProtError(
                f"UniProt {label} returned HTTP {exc.response.status_code}: {detail[:500]}"
            ) from exc
        except httpx.RequestError as exc:
            raise UniProtError(f"Could not reach UniProt {label}: {exc}") from exc

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
