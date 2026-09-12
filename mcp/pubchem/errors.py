"""Error types for the PubChem MCP server."""

from __future__ import annotations

from typing import Any


class PubChemError(Exception):
    """Raised when a PubChem request cannot be completed."""


class McpError(Exception):
    """JSON-RPC error with an MCP-compatible code."""

    def __init__(self, code: int, message: str, data: Any | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data
