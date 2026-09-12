"""Small RNAcentral REST API client."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from .constants import DEFAULT_TOOL_NAME, RNACENTRAL_API_BASE_URL, JsonObject
from .errors import RnaCentralError


@dataclass
class RnaCentralConfig:
    base_url: str = RNACENTRAL_API_BASE_URL
    contact: str | None = None
    tool: str = DEFAULT_TOOL_NAME
    timeout_seconds: float = 30.0
    max_retries: int = 2
    retry_base_seconds: float = 0.5

    @classmethod
    def from_env(cls) -> "RnaCentralConfig":
        return cls(
            base_url=os.environ.get("RNACENTRAL_API_BASE_URL", RNACENTRAL_API_BASE_URL),
            contact=os.environ.get("RNACENTRAL_CONTACT") or os.environ.get("NCBI_EMAIL") or os.environ.get("ENTREZ_EMAIL"),
            tool=os.environ.get("RNACENTRAL_TOOL", DEFAULT_TOOL_NAME),
        )


class RnaCentralClient:
    """REST client with conservative request pacing."""

    def __init__(
        self,
        config: RnaCentralConfig | None = None,
        *,
        opener: Callable[[urllib.request.Request, float], str | tuple[str, dict[str, str]]] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config or RnaCentralConfig.from_env()
        self._opener = opener
        self._sleep = sleep
        self._monotonic = monotonic
        self._last_request_at = 0.0

    @property
    def requests_per_second(self) -> int:
        return 3

    def request_json_with_headers(self, endpoint: str, params: JsonObject | None = None) -> tuple[Any, dict[str, str]]:
        return self._open_json(self._build_url(endpoint, params or {}), endpoint)

    def _open_json(self, url: str, label: str) -> tuple[Any, dict[str, str]]:
        self._throttle()
        text, response_headers = self._open_url(url, label, accept="application/json")
        if not text.strip():
            return {}, response_headers
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RnaCentralError(f"RNAcentral API {label} returned invalid JSON") from exc
        return payload, response_headers

    def _build_url(self, endpoint: str, params: JsonObject) -> str:
        endpoint = endpoint.lstrip("/")
        url = f"{self.config.base_url.rstrip('/')}/{endpoint}"
        if not params:
            return url
        encoded = urllib.parse.urlencode(params, doseq=True)
        return f"{url}?{encoded}"

    def _open_url(self, url: str, label: str, *, accept: str) -> tuple[str, dict[str, str]]:
        headers = {
            "Accept": accept,
            "User-Agent": self._user_agent(),
        }
        request = urllib.request.Request(url, headers=headers, method="GET")
        try:
            if self._opener is not None:
                opened = self._opener(request, self.config.timeout_seconds)
                if isinstance(opened, tuple):
                    return opened
                return opened, {}
            for attempt in range(self.config.max_retries + 1):
                try:
                    with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                        response_headers = {key.lower(): value for key, value in response.headers.items()}
                        text = response.read().decode("utf-8", errors="replace")
                        return text, response_headers
                except urllib.error.URLError:
                    if attempt >= self.config.max_retries:
                        raise
                    self._sleep(self.config.retry_base_seconds * (attempt + 1))
            raise RnaCentralError(f"Could not reach RNAcentral API {label}")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RnaCentralError(f"RNAcentral API {label} returned HTTP {exc.code}: {detail[:500]}") from exc
        except urllib.error.URLError as exc:
            raise RnaCentralError(f"Could not reach RNAcentral API {label}: {exc}") from exc

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

