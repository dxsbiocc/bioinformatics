"""Small ENCODE Portal REST client."""

from __future__ import annotations

import json
import os
import time
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from mcp.http_client import Opener, PacedHttpClient

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
        opener: Opener | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config or EncodeConfig.from_env()
        self._http = PacedHttpClient(
            error_class=EncodeError,
            service_name="ENCODE",
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
        text, response_headers = self._open_url(url, label, accept="application/json")
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise EncodeError(f"ENCODE {label} returned invalid JSON") from exc
        return payload, response_headers

    def _open_url(self, url: str, label: str, *, accept: str) -> tuple[str, dict[str, str]]:
        headers = {
            "Accept": accept,
            "User-Agent": self._user_agent(),
        }
        return self._http.send("GET", url, headers, label=label)

    def _user_agent(self) -> str:
        if self.config.contact:
            return f"{self.config.tool}/0.1 ({self.config.contact})"
        return f"{self.config.tool}/0.1"

