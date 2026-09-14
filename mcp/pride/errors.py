"""Error types for the PRIDE Archive MCP server."""

from __future__ import annotations

from mcp.http_client import UpstreamError
from mcp.rpc import McpError

__all__ = ["McpError", "PrideError"]


class PrideError(UpstreamError):
    """Raised when PRIDE Archive cannot satisfy a request."""
