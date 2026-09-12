"""Small NCBI E-utilities client."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Callable

from .constants import DEFAULT_TOOL_NAME, NCBI_EUTILS_BASE_URL, JsonObject
from .errors import NcbiError


@dataclass
class NcbiConfig:
    base_url: str = NCBI_EUTILS_BASE_URL
    api_key: str | None = None
    email: str | None = None
    tool: str = DEFAULT_TOOL_NAME
    timeout_seconds: float = 30.0

    @classmethod
    def from_env(cls) -> "NcbiConfig":
        return cls(
            api_key=os.environ.get("NCBI_API_KEY")
            or os.environ.get("ENTREZ_API_KEY"),
            email=os.environ.get("NCBI_EMAIL") or os.environ.get("ENTREZ_EMAIL"),
            tool=os.environ.get("NCBI_TOOL", DEFAULT_TOOL_NAME),
        )


class NcbiClient:
    """Small E-utilities client with NCBI-friendly request metadata."""

    def __init__(
        self,
        config: NcbiConfig | None = None,
        *,
        opener: Callable[[urllib.request.Request, float], str] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config or NcbiConfig.from_env()
        self._opener = opener
        self._sleep = sleep
        self._monotonic = monotonic
        self._last_request_at = 0.0

    @property
    def requests_per_second(self) -> int:
        return 10 if self.config.api_key else 3

    def request_text(self, endpoint: str, params: JsonObject) -> str:
        self._throttle()
        url = self._build_url(endpoint, params)
        return self._open_url(url, endpoint)

    def request_url_text(
        self,
        url: str,
        params: JsonObject,
        *,
        label: str = "request",
        include_api_key: bool = False,
    ) -> str:
        self._throttle()
        query: JsonObject = {
            **params,
            "tool": self.config.tool,
        }
        if self.config.email:
            query["email"] = self.config.email
        if include_api_key and self.config.api_key:
            query["api_key"] = self.config.api_key
        encoded = urllib.parse.urlencode(query, doseq=True)
        separator = "&" if "?" in url else "?"
        return self._open_url(f"{url}{separator}{encoded}", label)

    def request_url_json(
        self,
        url: str,
        params: JsonObject,
        *,
        label: str = "request",
        include_api_key: bool = False,
    ) -> JsonObject:
        text = self.request_url_text(
            url,
            params,
            label=label,
            include_api_key=include_api_key,
        )
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise NcbiError(f"NCBI {label} returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise NcbiError(f"NCBI {label} returned non-object JSON")
        return payload

    def _open_url(self, url: str, label: str) -> str:
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json, application/xml, text/plain",
                "User-Agent": self._user_agent(),
            },
        )
        try:
            if self._opener is not None:
                return self._opener(request, self.config.timeout_seconds)
            with urllib.request.urlopen(
                request,
                timeout=self.config.timeout_seconds,
            ) as response:
                return response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise NcbiError(
                f"NCBI {label} returned HTTP {exc.code}: {detail[:500]}"
            ) from exc
        except urllib.error.URLError as exc:
            raise NcbiError(f"Could not reach NCBI {label}: {exc}") from exc

    def request_json(self, endpoint: str, params: JsonObject) -> JsonObject:
        text = self.request_text(endpoint, params)
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise NcbiError(f"NCBI {endpoint} returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise NcbiError(f"NCBI {endpoint} returned non-object JSON")
        return payload

    def _build_url(self, endpoint: str, params: JsonObject) -> str:
        query: JsonObject = {
            **params,
            "tool": self.config.tool,
        }
        if self.config.email:
            query["email"] = self.config.email
        if self.config.api_key:
            query["api_key"] = self.config.api_key
        encoded = urllib.parse.urlencode(query, doseq=True)
        return f"{self.config.base_url.rstrip('/')}/{endpoint}?{encoded}"

    def _throttle(self) -> None:
        minimum_interval = 1.0 / self.requests_per_second
        now = self._monotonic()
        elapsed = now - self._last_request_at
        if elapsed < minimum_interval:
            self._sleep(minimum_interval - elapsed)
        self._last_request_at = self._monotonic()

    def _user_agent(self) -> str:
        if self.config.email:
            return f"{self.config.tool}/0.1 ({self.config.email})"
        return f"{self.config.tool}/0.1"
