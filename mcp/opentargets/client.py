"""Small Open Targets GraphQL client."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass

from mcp.http_client import Opener, PacedHttpClient

from .constants import (
    DEFAULT_TOOL_NAME,
    OPENTARGETS_GRAPHQL_URL,
    OPENTARGETS_WEBSITE_BASE_URL,
    JsonObject,
)
from .errors import OpenTargetsError


@dataclass
class OpenTargetsConfig:
    graphql_url: str = OPENTARGETS_GRAPHQL_URL
    website_base_url: str = OPENTARGETS_WEBSITE_BASE_URL
    contact: str | None = None
    tool: str = DEFAULT_TOOL_NAME
    timeout_seconds: float = 30.0
    max_retries: int = 2
    retry_base_seconds: float = 0.75

    @classmethod
    def from_env(cls) -> OpenTargetsConfig:
        return cls(
            graphql_url=os.environ.get("OPENTARGETS_GRAPHQL_URL", OPENTARGETS_GRAPHQL_URL),
            website_base_url=os.environ.get(
                "OPENTARGETS_WEBSITE_BASE_URL",
                OPENTARGETS_WEBSITE_BASE_URL,
            ),
            contact=os.environ.get("OPENTARGETS_CONTACT")
            or os.environ.get("UNIPROT_CONTACT")
            or os.environ.get("NCBI_EMAIL")
            or os.environ.get("ENTREZ_EMAIL"),
            tool=os.environ.get("OPENTARGETS_TOOL", DEFAULT_TOOL_NAME),
        )


class OpenTargetsClient:
    """GraphQL client with conservative request pacing."""

    def __init__(
        self,
        config: OpenTargetsConfig | None = None,
        *,
        opener: Opener | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config or OpenTargetsConfig.from_env()
        self._http = PacedHttpClient(
            error_class=OpenTargetsError,
            service_name="Open Targets",
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

    def request_graphql_with_headers(
        self,
        query: str,
        variables: JsonObject | None = None,
    ) -> tuple[JsonObject, dict[str, str]]:
        payload = json.dumps(
            {"query": query, "variables": variables or {}},
            separators=(",", ":"),
        ).encode("utf-8")
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": self._user_agent(),
        }
        text, response_headers = self._http.send(
            "POST", self.config.graphql_url, headers, content=payload, label="graphql"
        )
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise OpenTargetsError("Open Targets GraphQL returned invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise OpenTargetsError("Open Targets GraphQL returned non-object JSON")
        return parsed, response_headers

    def _user_agent(self) -> str:
        if self.config.contact:
            return f"{self.config.tool}/0.1 ({self.config.contact})"
        return f"{self.config.tool}/0.1"
