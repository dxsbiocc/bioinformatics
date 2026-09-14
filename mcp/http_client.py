"""Shared paced, retrying httpx client used by every bundled MCP server.

Every server's client.py built its own httpx.Client lifecycle, request
pacing, retry loop, and error mapping by hand (a leftover from migrating
each one off urllib independently). This module holds that once: each
server's client.py now just builds URLs/headers/bodies for its API and
calls PacedHttpClient.send(), then does its own JSON decoding.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import httpx

# A test-injected transport: given the outgoing request and the configured
# timeout, return either the response body text, or (text, headers) when the
# caller needs response headers (e.g. to detect a Cloudflare challenge).
Opener = Callable[[httpx.Request, float], Any]


class UpstreamError(Exception):
    """Base class for a server's own <X>Error, raised when the upstream API
    cannot satisfy a request. Each server subclasses this so callers can
    still catch a server-specific type, but the HTTP context it carries
    (status code, endpoint label, response body, response headers) is
    uniform across all of them.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        endpoint: str = "",
        response_body: str = "",
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.endpoint = endpoint
        self.response_body = response_body
        self.headers = headers or {}


class PacedHttpClient:
    """A reused httpx.Client(http2=True) with request pacing, bounded
    retries on transport failures (not HTTP status errors - those propagate
    immediately), and uniform error mapping to a server-supplied
    UpstreamError subclass.
    """

    def __init__(
        self,
        *,
        error_class: type[UpstreamError],
        service_name: str,
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
        retry_base_seconds: float = 0.5,
        requests_per_second: float = 3.0,
        opener: Opener | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.error_class = error_class
        self.service_name = service_name
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_base_seconds = retry_base_seconds
        self.requests_per_second = requests_per_second
        self.opener = opener
        self.sleep = sleep
        self.monotonic = monotonic
        # Test seam: httpx.MockTransport, so tests can exercise the real
        # retry/error-mapping logic below without touching the network.
        self._transport = transport
        self._last_request_at = 0.0
        self._http: httpx.Client | None = None

    @property
    def _client(self) -> httpx.Client:
        if self._http is None:
            self._http = httpx.Client(
                http2=True,
                timeout=httpx.Timeout(self.timeout_seconds),
                transport=self._transport,
            )
        return self._http

    def close(self) -> None:
        if self._http is not None:
            self._http.close()
            self._http = None

    def throttle(self) -> None:
        minimum_interval = 1.0 / max(self.requests_per_second, 0.001)
        now = self.monotonic()
        elapsed = now - self._last_request_at
        if elapsed < minimum_interval:
            self.sleep(minimum_interval - elapsed)
        self._last_request_at = self.monotonic()

    def send(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        *,
        content: bytes | None = None,
        label: str,
    ) -> tuple[str, dict[str, str]]:
        self.throttle()
        request = httpx.Request(method, url, headers=headers, content=content)
        try:
            if self.opener is not None:
                opened = self.opener(request, self.timeout_seconds)
                if isinstance(opened, tuple) and len(opened) == 2:
                    return str(opened[0]), dict(opened[1])
                return str(opened), {}
            for attempt in range(self.max_retries + 1):
                try:
                    response = self._client.send(request)
                    response.raise_for_status()
                    response_headers = {key.lower(): value for key, value in response.headers.items()}
                    text = response.read().decode("utf-8", errors="replace")
                    return text, response_headers
                except httpx.RequestError:
                    if attempt >= self.max_retries:
                        raise
                    self.sleep(self.retry_base_seconds * (attempt + 1))
            raise self.error_class(f"Could not reach {self.service_name} {label}", endpoint=label)
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text
            raise self.error_class(
                f"{self.service_name} {label} returned HTTP {exc.response.status_code}: {detail[:500]}",
                status_code=exc.response.status_code,
                endpoint=label,
                response_body=detail[:1000],
                headers={key.lower(): value for key, value in exc.response.headers.items()},
            ) from exc
        except httpx.RequestError as exc:
            raise self.error_class(f"Could not reach {self.service_name} {label}: {exc}", endpoint=label) from exc
