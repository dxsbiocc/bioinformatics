"""cBioPortal MCP error types."""

from __future__ import annotations

from typing import Any


class CbioPortalError(Exception):
    """Raised when cBioPortal retrieval or normalization fails."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        endpoint: str = "",
        response_body: str = "",
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.endpoint = endpoint
        self.response_body = response_body


class McpError(Exception):
    """JSON-RPC error surfaced at the MCP boundary."""

    def __init__(self, code: int, message: str, data: Any | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data
