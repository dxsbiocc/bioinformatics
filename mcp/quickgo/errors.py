"""Error types for the QuickGO MCP server."""

from __future__ import annotations

from mcp.http_client import UpstreamError
from mcp.rpc import McpError

__all__ = ["McpError", "QuickGoError"]


class QuickGoError(UpstreamError):
    """Raised when QuickGO cannot satisfy a request."""
