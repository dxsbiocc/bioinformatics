"""Small KEGG REST API client."""

from __future__ import annotations

import os
import time
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass

from mcp.http_client import Opener, PacedHttpClient

from .constants import DEFAULT_TOOL_NAME, KEGG_REST_BASE_URL, KEGG_WEBSITE_BASE_URL
from .errors import KeggError
from .utils import quote_segment


@dataclass
class KeggConfig:
    base_url: str = KEGG_REST_BASE_URL
    website_base_url: str = KEGG_WEBSITE_BASE_URL
    contact: str | None = None
    tool: str = DEFAULT_TOOL_NAME
    timeout_seconds: float = 30.0
    max_retries: int = 2
    retry_base_seconds: float = 0.5
    requests_per_second: float = 3.0

    @classmethod
    def from_env(cls) -> KeggConfig:
        return cls(
            base_url=os.environ.get("KEGG_REST_BASE_URL", KEGG_REST_BASE_URL),
            website_base_url=os.environ.get("KEGG_WEBSITE_BASE_URL", KEGG_WEBSITE_BASE_URL),
            contact=os.environ.get("KEGG_CONTACT")
            or os.environ.get("NCBI_EMAIL")
            or os.environ.get("ENTREZ_EMAIL"),
            tool=os.environ.get("KEGG_TOOL", DEFAULT_TOOL_NAME),
            requests_per_second=parse_float_env("KEGG_REQUESTS_PER_SECOND", 3.0),
        )


class KeggClient:
    """Small text REST client with KEGG's conservative request pacing."""

    def __init__(
        self,
        config: KeggConfig | None = None,
        *,
        opener: Opener | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config or KeggConfig.from_env()
        self._http = PacedHttpClient(
            error_class=KeggError,
            service_name="KEGG",
            timeout_seconds=self.config.timeout_seconds,
            max_retries=self.config.max_retries,
            retry_base_seconds=self.config.retry_base_seconds,
            requests_per_second=max(float(self.config.requests_per_second or 1), 0.1),
            opener=opener,
            sleep=sleep,
            monotonic=monotonic,
        )

    def close(self) -> None:
        self._http.close()

    @property
    def requests_per_second(self) -> float:
        return self.config.requests_per_second

    def request_text_with_headers(
        self,
        operation: str,
        segments: list[str],
    ) -> tuple[str, dict[str, str], str, str]:
        endpoint = "/".join([operation.strip("/"), *[str(segment).strip("/") for segment in segments if str(segment)]])
        url = self.build_url(operation, segments)
        text, headers = self._open_url(url, endpoint)
        return text, headers, endpoint, url

    def build_url(self, operation: str, segments: list[str]) -> str:
        quoted = [quote_segment(operation.strip("/"))]
        quoted.extend(quote_segment(segment.strip("/")) for segment in segments if str(segment))
        return f"{self.config.base_url.rstrip('/')}/{'/'.join(quoted)}"

    def entry_url(self, entry_id: str) -> str:
        return f"{self.config.website_base_url.rstrip('/')}/entry/{urllib.parse.quote(entry_id, safe=':._-')}"

    def _open_url(self, url: str, label: str) -> tuple[str, dict[str, str]]:
        headers = {
            "Accept": "text/plain,application/json,*/*",
            "User-Agent": self._user_agent(),
        }
        return self._http.send("GET", url, headers, label=label)

    def _user_agent(self) -> str:
        if self.config.contact:
            return f"{self.config.tool}/0.1 ({self.config.contact})"
        return f"{self.config.tool}/0.1"


def parse_float_env(name: str, default: float) -> float:
    value = os.environ.get(name)
    if not value:
        return default
    try:
        parsed = float(value)
    except ValueError:
        return default
    return min(max(parsed, 0.1), 3.0)
