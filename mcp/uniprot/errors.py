"""Error types used at the MCP and UniProt boundaries."""

from __future__ import annotations

from typing import Any


class McpError(Exception):
    """JSON-RPC error with an MCP-compatible code."""

    def __init__(self, code: int, message: str, data: Any | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


class UniProtError(Exception):
    """Raised when a UniProt request fails or returns malformed data."""

