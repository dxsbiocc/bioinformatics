"""ChEBI MCP errors."""

from __future__ import annotations

from typing import Any


class ChebiError(Exception):
    """Raised when ChEBI cannot return usable data."""


class McpError(Exception):
    """JSON-RPC error with MCP-compatible fields."""

    def __init__(self, code: int, message: str, data: Any | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data

