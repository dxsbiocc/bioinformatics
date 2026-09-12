"""Error types for the bioRxiv/medRxiv MCP server."""

from __future__ import annotations

from typing import Any


class McpError(Exception):
    def __init__(self, code: int, message: str, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


class BioRxivError(Exception):
    """Raised when bioRxiv/medRxiv cannot satisfy a request."""

