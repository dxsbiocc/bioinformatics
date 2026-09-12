"""Error types used at the MCP and NCBI boundaries."""

from __future__ import annotations

from typing import Any


class McpError(Exception):
    """JSON-RPC error with an MCP-compatible code."""

    def __init__(self, code: int, message: str, data: Any | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


class NcbiError(Exception):
    """Raised when an NCBI request fails or returns malformed data."""
