"""Error types for the gnomAD MCP server."""

from __future__ import annotations

from mcp.http_client import UpstreamError
from mcp.rpc import McpError

__all__ = ["McpError", "GnomadError"]


class GnomadError(UpstreamError):
    """Raised when a gnomAD request cannot be completed."""
