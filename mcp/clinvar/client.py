"""Small ClinVar API client."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from .constants import (
    CLINICAL_TABLES_URL,
    DEFAULT_TOOL_NAME,
    EUTILS_BASE_URL,
    NCBI_WEBSITE_BASE_URL,
    JsonObject,
)
from .errors import ClinvarError


@dataclass
class ClinvarConfig:
    clinical_tables_url: str = CLINICAL_TABLES_URL
    eutils_base_url: str = EUTILS_BASE_URL
    ncbi_website_base_url: str = NCBI_WEBSITE_BASE_URL
    api_key: str | None = None
    email: str | None = None
    tool: str = DEFAULT_TOOL_NAME
    timeout_seconds: float = 30.0
    max_retries: int = 2
    retry_base_seconds: float = 0.5

    @classmethod
    def from_env(cls) -> "ClinvarConfig":
        return cls(
            clinical_tables_url=os.environ.get("CLINVAR_CLINICAL_TABLES_URL", CLINICAL_TABLES_URL),
            eutils_base_url=os.environ.get("CLINVAR_EUTILS_BASE_URL", EUTILS_BASE_URL),
            ncbi_website_base_url=os.environ.get("CLINVAR_NCBI_WEBSITE_BASE_URL", NCBI_WEBSITE_BASE_URL),
            api_key=os.environ.get("CLINVAR_API_KEY")
            or os.environ.get("NCBI_API_KEY")
            or os.environ.get("ENTREZ_API_KEY"),
            email=os.environ.get("CLINVAR_EMAIL")
            or os.environ.get("NCBI_EMAIL")
            or os.environ.get("ENTREZ_EMAIL"),
            tool=os.environ.get("CLINVAR_TOOL", DEFAULT_TOOL_NAME),
        )


class ClinvarClient:
    """Small REST client with conservative request pacing."""

    def __init__(
        self,
        config: ClinvarConfig | None = None,
        *,
        opener: Callable[[urllib.request.Request, float], str] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config or ClinvarConfig.from_env()
        self._opener = opener
        self._sleep = sleep
        self._monotonic = monotonic
        self._last_request_at = 0.0

    @property
    def requests_per_second(self) -> int:
        return 3 if not self.config.api_key else 10

    def request_clinical_tables_with_headers(
        self,
        params: JsonObject,
    ) -> tuple[Any, dict[str, str]]:
        return self._open_json(self._build_url(self.config.clinical_tables_url, params), "clinicaltables/search")

    def request_eutils_json_with_headers(
        self,
        endpoint: str,
        params: JsonObject,
    ) -> tuple[JsonObject, dict[str, str]]:
        endpoint = endpoint.lstrip("/")
        url = f"{self.config.eutils_base_url.rstrip('/')}/{endpoint}"
        params = dict(params)
        params.setdefault("retmode", "json")
        params.setdefault("tool", self.config.tool)
        if self.config.email:
            params.setdefault("email", self.config.email)
        if self.config.api_key:
            params.setdefault("api_key", self.config.api_key)
        payload, headers = self._open_json(self._build_url(url, params), endpoint)
        if not isinstance(payload, dict):
            raise ClinvarError(f"ClinVar {endpoint} returned non-object JSON")
        return payload, headers

    def _open_json(self, url: str, label: str) -> tuple[Any, dict[str, str]]:
        self._throttle()
        text, response_headers = self._open_url(url, label, accept="application/json")
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ClinvarError(f"ClinVar {label} returned invalid JSON") from exc
        return payload, response_headers

    def _build_url(self, url: str, params: JsonObject) -> str:
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
                return self._opener(request, self.config.timeout_seconds), {}
            for attempt in range(self.config.max_retries + 1):
                try:
                    with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                        response_headers = {
                            key.lower(): value
                            for key, value in response.headers.items()
                        }
                        text = response.read().decode("utf-8", errors="replace")
                        return text, response_headers
                except urllib.error.URLError:
                    if attempt >= self.config.max_retries:
                        raise
                    self._sleep(self.config.retry_base_seconds * (attempt + 1))
            raise ClinvarError(f"Could not reach ClinVar {label}")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ClinvarError(
                f"ClinVar {label} returned HTTP {exc.code}: {detail[:500]}"
            ) from exc
        except urllib.error.URLError as exc:
            raise ClinvarError(f"Could not reach ClinVar {label}: {exc}") from exc

    def _throttle(self) -> None:
        minimum_interval = 1.0 / self.requests_per_second
        now = self._monotonic()
        elapsed = now - self._last_request_at
        if elapsed < minimum_interval:
            self._sleep(minimum_interval - elapsed)
        self._last_request_at = self._monotonic()

    def _user_agent(self) -> str:
        if self.config.email:
            return f"{self.config.tool}/0.1 ({self.config.email})"
        return f"{self.config.tool}/0.1"

