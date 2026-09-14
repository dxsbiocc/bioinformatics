"""Small cBioPortal REST API client."""

from __future__ import annotations

import json
import os
import time
import urllib.parse
from dataclasses import dataclass
from typing import Any, Callable

import httpx

from .constants import CBIOPORTAL_API_BASE_URL, CBIOPORTAL_WEBSITE_BASE_URL, DEFAULT_TOOL_NAME, JsonObject
from .errors import CbioPortalError


@dataclass
class CbioPortalConfig:
    api_base_url: str = CBIOPORTAL_API_BASE_URL
    website_base_url: str = CBIOPORTAL_WEBSITE_BASE_URL
    contact: str | None = None
    tool: str = DEFAULT_TOOL_NAME
    timeout_seconds: float = 30.0
    max_retries: int = 2
    retry_base_seconds: float = 0.5

    @classmethod
    def from_env(cls) -> "CbioPortalConfig":
        return cls(
            api_base_url=os.environ.get("CBIOPORTAL_API_BASE_URL", CBIOPORTAL_API_BASE_URL),
            website_base_url=os.environ.get("CBIOPORTAL_WEBSITE_BASE_URL", CBIOPORTAL_WEBSITE_BASE_URL),
            contact=os.environ.get("CBIOPORTAL_CONTACT")
            or os.environ.get("NCBI_EMAIL")
            or os.environ.get("UNIPROT_CONTACT"),
            tool=os.environ.get("CBIOPORTAL_TOOL", DEFAULT_TOOL_NAME),
        )


class CbioPortalClient:
    """REST client with conservative request pacing."""

    def __init__(
        self,
        config: CbioPortalConfig | None = None,
        *,
        opener: Callable[[httpx.Request, float], str] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config or CbioPortalConfig.from_env()
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

    def request_json_with_headers(
        self,
        endpoint: str,
        params: JsonObject | None = None,
        *,
        method: str = "GET",
        json_body: JsonObject | list[Any] | None = None,
    ) -> tuple[Any, dict[str, str]]:
        return self._open_json(self.build_url(endpoint, params or {}), endpoint, method=method, json_body=json_body)

    def build_url(self, endpoint: str, params: JsonObject | None = None) -> str:
        endpoint = endpoint.lstrip("/")
        url = f"{self.config.api_base_url.rstrip('/')}/{endpoint}"
        if not params:
            return url
        encoded = urllib.parse.urlencode(params, doseq=True)
        return f"{url}?{encoded}"

    def study_url(self, study_id: str) -> str:
        return f"{self.config.website_base_url.rstrip('/')}/study/summary?id={urllib.parse.quote(study_id)}"

    def _open_json(
        self,
        url: str,
        label: str,
        *,
        method: str,
        json_body: JsonObject | list[Any] | None,
    ) -> tuple[Any, dict[str, str]]:
        self._throttle()
        text, response_headers = self._open_url(url, label, method=method, json_body=json_body)
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise CbioPortalError(f"cBioPortal {label} returned invalid JSON") from exc
        return payload, response_headers

    def _open_url(
        self,
        url: str,
        label: str,
        *,
        method: str,
        json_body: JsonObject | list[Any] | None,
    ) -> tuple[str, dict[str, str]]:
        data = json.dumps(json_body).encode("utf-8") if json_body is not None else None
        headers = {"Accept": "application/json", "User-Agent": self._user_agent()}
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = httpx.Request(method.upper(), url, headers=headers, content=data)
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
            raise CbioPortalError(f"Could not reach cBioPortal {label}")
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text
            raise CbioPortalError(
                f"cBioPortal {label} returned HTTP {exc.response.status_code}: {detail[:500]}",
                status_code=exc.response.status_code,
                endpoint=label,
                response_body=detail,
            ) from exc
        except httpx.RequestError as exc:
            raise CbioPortalError(f"Could not reach cBioPortal {label}: {exc}") from exc

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
