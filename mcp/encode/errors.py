"""ENCODE MCP error types."""

from __future__ import annotations

from mcp.http_client import UpstreamError
from mcp.rpc import McpError

__all__ = ["McpError", "EncodeError"]


class EncodeError(UpstreamError):
    """Raised when ENCODE retrieval or normalization fails."""
