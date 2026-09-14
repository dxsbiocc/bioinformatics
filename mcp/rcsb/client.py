"""Small RCSB PDB API client."""

from __future__ import annotations

import json
import os
import time
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass

from mcp.http_client import Opener, PacedHttpClient

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
        opener: Opener | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config or RcsbConfig.from_env()
        self._http = PacedHttpClient(
            error_class=RcsbError,
            service_name="RCSB",
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
        return self._http.send(method, url, headers, content=body, label=label)

    def _user_agent(self) -> str:
        if self.config.contact:
            return f"{self.config.tool}/0.1 ({self.config.contact})"
        return f"{self.config.tool}/0.1"
