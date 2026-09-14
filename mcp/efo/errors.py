"""Error types for the EFO MCP server."""

from __future__ import annotations

from mcp.http_client import UpstreamError
from mcp.rpc import McpError

__all__ = ["McpError", "EfoError"]


class EfoError(UpstreamError):
    """Raised when OLS4/EFO cannot satisfy a request."""
