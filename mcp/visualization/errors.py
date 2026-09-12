"""Errors raised across the omics visualization MCP boundary."""

from __future__ import annotations

from typing import Any


class VisualizationError(Exception):
    """Raised when visualization routing cannot inspect local inputs."""


class McpError(Exception):
    """JSON-RPC error with an MCP-compatible code and optional data."""

    def __init__(self, code: int, message: str, data: Any | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data
