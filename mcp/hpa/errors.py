"""Error types for the Human Protein Atlas MCP server."""

from __future__ import annotations

from typing import Any


class McpError(Exception):
    def __init__(self, code: int, message: str, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


class HpaError(Exception):
    """Raised when Human Protein Atlas cannot satisfy a request."""

