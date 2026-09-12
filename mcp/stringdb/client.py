"""Small STRING API client."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Callable

from .constants import (
    DEFAULT_CALLER_IDENTITY,
    DEFAULT_TOOL_NAME,
    STRING_API_BASE_URL,
    JsonObject,
)
from .errors import StringDbError


@dataclass
class StringDbConfig:
    base_url: str = STRING_API_BASE_URL
    caller_identity: str = DEFAULT_CALLER_IDENTITY
    contact: str | None = None
    tool: str = DEFAULT_TOOL_NAME
    timeout_seconds: float = 30.0
    max_retries: int = 2
    retry_base_seconds: float = 0.5

    @classmethod
    def from_env(cls) -> "StringDbConfig":
        return cls(
            base_url=os.environ.get("STRING_BASE_URL", STRING_API_BASE_URL),
            caller_identity=os.environ.get(
                "STRING_CALLER_IDENTITY",
                DEFAULT_CALLER_IDENTITY,
            ),
            contact=os.environ.get("STRING_CONTACT")
            or os.environ.get("UNIPROT_CONTACT")
            or os.environ.get("NCBI_EMAIL")
            or os.environ.get("ENTREZ_EMAIL"),
            tool=os.environ.get("STRING_TOOL", DEFAULT_TOOL_NAME),
        )


class StringDbClient:
    """Small REST client with conservative request pacing."""

    def __init__(
        self,
        config: StringDbConfig | None = None,
        *,
        opener: Callable[[urllib.request.Request, float], str] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config or StringDbConfig.from_env()
        self._opener = opener
        self._sleep = sleep
        self._monotonic = monotonic
        self._last_request_at = 0.0

    @property
    def requests_per_second(self) -> int:
        return 1

    def request_json_array_with_headers(
        self,
        endpoint: str,
        params: JsonObject | None = None,
    ) -> tuple[list[JsonObject], dict[str, str]]:
        text, headers = self.request_text_with_headers(
            endpoint,
            params or {},
            accept="application/json",
        )
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise StringDbError(f"STRING {endpoint} returned invalid JSON") from exc
        if not isinstance(payload, list):
            raise StringDbError(f"STRING {endpoint} returned non-array JSON")
        return [item for item in payload if isinstance(item, dict)], headers

    def request_text_with_headers(
        self,
        endpoint: str,
        params: JsonObject | None = None,
        *,
        accept: str = "text/plain",
    ) -> tuple[str, dict[str, str]]:
        self._throttle()
        merged_params = dict(params or {})
        merged_params.setdefault("caller_identity", self.config.caller_identity)
        url = self._build_url(endpoint, merged_params)
        return self._open_url(url, endpoint, accept)

    def _build_url(self, endpoint: str, params: JsonObject) -> str:
        endpoint = endpoint.lstrip("/")
        url = f"{self.config.base_url.rstrip('/')}/{endpoint}"
        if not params:
            return url
        encoded = urllib.parse.urlencode(params, doseq=True)
        return f"{url}?{encoded}"

    def _open_url(self, url: str, label: str, accept: str) -> tuple[str, dict[str, str]]:
        request = urllib.request.Request(
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
                    with urllib.request.urlopen(
                        request,
                        timeout=self.config.timeout_seconds,
                    ) as response:
                        headers = {
                            key.lower(): value
                            for key, value in response.headers.items()
                        }
                        text = response.read().decode("utf-8", errors="replace")
                        return text, headers
                except urllib.error.URLError:
                    if attempt >= self.config.max_retries:
                        raise
                    self._sleep(self.config.retry_base_seconds * (attempt + 1))
            raise StringDbError(f"Could not reach STRING {label}")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise StringDbError(
                f"STRING {label} returned HTTP {exc.code}: {detail[:500]}"
            ) from exc
        except urllib.error.URLError as exc:
            raise StringDbError(f"Could not reach STRING {label}: {exc}") from exc

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

