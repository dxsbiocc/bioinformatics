"""Error types for the RNAcentral MCP server."""

from __future__ import annotations

from typing import Any


class McpError(Exception):
    def __init__(self, code: int, message: str, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


class RnaCentralError(Exception):
    """Raised when RNAcentral cannot satisfy a request."""

