"""AlphaFold MCP exceptions."""

from __future__ import annotations

from typing import Any


class McpError(Exception):
    """JSON-RPC error with a protocol code."""

    def __init__(self, code: int, message: str, data: Any | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


class AlphaFoldError(Exception):
    """Raised for AlphaFold API and normalization failures."""

