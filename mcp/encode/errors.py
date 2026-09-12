"""ENCODE MCP error types."""

from __future__ import annotations

from typing import Any


class EncodeError(Exception):
    """Raised when ENCODE retrieval or normalization fails."""


class McpError(Exception):
    """JSON-RPC error surfaced at the MCP boundary."""

    def __init__(self, code: int, message: str, data: Any | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data

