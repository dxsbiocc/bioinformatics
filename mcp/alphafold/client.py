"""Small AlphaFold DB API client."""

from __future__ import annotations

import json
import os
import time
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass

from mcp.http_client import Opener, PacedHttpClient

from .constants import ALPHAFOLD_API_BASE_URL, DEFAULT_TOOL_NAME, JsonObject
from .errors import AlphaFoldError


@dataclass
class AlphaFoldConfig:
    base_url: str = ALPHAFOLD_API_BASE_URL
    contact: str | None = None
    tool: str = DEFAULT_TOOL_NAME
    timeout_seconds: float = 30.0
    max_retries: int = 2
    retry_base_seconds: float = 0.5

    @classmethod
    def from_env(cls) -> AlphaFoldConfig:
        return cls(
            base_url=os.environ.get("ALPHAFOLD_BASE_URL", ALPHAFOLD_API_BASE_URL),
            contact=os.environ.get("ALPHAFOLD_CONTACT")
            or os.environ.get("UNIPROT_CONTACT")
            or os.environ.get("NCBI_EMAIL")
            or os.environ.get("ENTREZ_EMAIL"),
            tool=os.environ.get("ALPHAFOLD_TOOL", DEFAULT_TOOL_NAME),
        )


class AlphaFoldClient:
    """Small REST client with conservative request pacing."""

    def __init__(
        self,
        config: AlphaFoldConfig | None = None,
        *,
        opener: Opener | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config or AlphaFoldConfig.from_env()
        self._http = PacedHttpClient(
            error_class=AlphaFoldError,
            service_name="AlphaFold",
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
            raise AlphaFoldError(f"AlphaFold {endpoint} returned invalid JSON") from exc
        if not isinstance(payload, list):
            raise AlphaFoldError(f"AlphaFold {endpoint} returned non-array JSON")
        return [item for item in payload if isinstance(item, dict)], headers

    def request_text_with_headers(
        self,
        endpoint: str,
        params: JsonObject | None = None,
        *,
        accept: str = "text/plain",
    ) -> tuple[str, dict[str, str]]:
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
        headers = {
            "Accept": accept,
            "User-Agent": self._user_agent(),
        }
        return self._http.send("GET", url, headers, label=label)

    def _user_agent(self) -> str:
        if self.config.contact:
            return f"{self.config.tool}/0.1 ({self.config.contact})"
        return f"{self.config.tool}/0.1"
