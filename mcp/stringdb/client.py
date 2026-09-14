"""Small STRING API client."""

from __future__ import annotations

import json
import os
import time
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass

from mcp.http_client import Opener, PacedHttpClient

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
    def from_env(cls) -> StringDbConfig:
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
        opener: Opener | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config or StringDbConfig.from_env()
        self._http = PacedHttpClient(
            error_class=StringDbError,
            service_name="STRING",
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
        headers = {
            "Accept": accept,
            "User-Agent": self._user_agent(),
        }
        return self._http.send("GET", url, headers, label=label)

    def _user_agent(self) -> str:
        if self.config.contact:
            return f"{self.config.tool}/0.1 ({self.config.contact})"
        return f"{self.config.tool}/0.1"

