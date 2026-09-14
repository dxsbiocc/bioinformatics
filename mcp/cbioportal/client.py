"""Small cBioPortal REST API client."""

from __future__ import annotations

import json
import os
import time
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from mcp.http_client import Opener, PacedHttpClient

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
    def from_env(cls) -> CbioPortalConfig:
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
        opener: Opener | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config or CbioPortalConfig.from_env()
        self._http = PacedHttpClient(
            error_class=CbioPortalError,
            service_name="cBioPortal",
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
        return self._http.send(method.upper(), url, headers, content=data, label=label)

    def _user_agent(self) -> str:
        if self.config.contact:
            return f"{self.config.tool}/0.1 ({self.config.contact})"
        return f"{self.config.tool}/0.1"
