"""Small ChEBI REST client for public EBI endpoints."""

from __future__ import annotations

import json
import os
import time
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from mcp.http_client import Opener, PacedHttpClient

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
    def from_env(cls) -> ChebiConfig:
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
        opener: Opener | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config or ChebiConfig.from_env()
        self._http = PacedHttpClient(
            error_class=ChebiError,
            service_name="ChEBI",
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

    def request_json_with_headers(self, endpoint: str, params: JsonObject | None = None) -> tuple[Any, dict[str, str], str]:
        query = params or {}
        url = self._build_url(endpoint, query)
        payload, headers = self._open_json(url, endpoint)
        return payload, headers, url

    def _open_json(self, url: str, label: str) -> tuple[Any, dict[str, str]]:
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
        headers = {
            "Accept": accept,
            "User-Agent": self._user_agent(),
        }
        return self._http.send("GET", url, headers, label=label)

    def _user_agent(self) -> str:
        if self.config.contact:
            return f"{self.config.tool}/0.1 ({self.config.contact})"
        return f"{self.config.tool}/0.1"
