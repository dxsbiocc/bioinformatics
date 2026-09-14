"""Small Open Targets GraphQL client."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Callable

import httpx

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
    def from_env(cls) -> "OpenTargetsConfig":
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
        opener: Callable[[httpx.Request, float], str] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config or OpenTargetsConfig.from_env()
        self._opener = opener
        self._sleep = sleep
        self._monotonic = monotonic
        self._last_request_at = 0.0
        self._http: httpx.Client | None = None

    @property
    def _client(self) -> httpx.Client:
        if self._http is None:
            self._http = httpx.Client(
                http2=True,
                timeout=httpx.Timeout(self.config.timeout_seconds),
            )
        return self._http

    def close(self) -> None:
        if self._http is not None:
            self._http.close()
            self._http = None

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
        self._throttle()
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": self._user_agent(),
        }
        request = httpx.Request(
            "POST",
            self.config.graphql_url,
            headers=headers,
            content=payload,
        )
        text, response_headers = self._open_request(request, "graphql")
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise OpenTargetsError("Open Targets GraphQL returned invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise OpenTargetsError("Open Targets GraphQL returned non-object JSON")
        return parsed, response_headers

    def _open_request(
        self,
        request: httpx.Request,
        label: str,
    ) -> tuple[str, dict[str, str]]:
        try:
            if self._opener is not None:
                return self._opener(request, self.config.timeout_seconds), {}
            for attempt in range(self.config.max_retries + 1):
                try:
                    response = self._client.send(request)
                    response.raise_for_status()
                    response_headers = {
                        key.lower(): value
                        for key, value in response.headers.items()
                    }
                    text = response.read().decode("utf-8", errors="replace")
                    return text, response_headers
                except httpx.RequestError:
                    if attempt >= self.config.max_retries:
                        raise
                    self._sleep(self.config.retry_base_seconds * (attempt + 1))
            raise OpenTargetsError(f"Could not reach Open Targets {label}")
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text
            raise OpenTargetsError(
                f"Open Targets {label} returned HTTP {exc.response.status_code}: {detail[:500]}"
            ) from exc
        except httpx.RequestError as exc:
            raise OpenTargetsError(f"Could not reach Open Targets {label}: {exc}") from exc

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
