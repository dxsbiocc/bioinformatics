"""Error types for the RNAcentral MCP server."""

from __future__ import annotations

from mcp.http_client import UpstreamError
from mcp.rpc import McpError

__all__ = ["McpError", "RnaCentralError"]


class RnaCentralError(UpstreamError):
    """Raised when RNAcentral cannot satisfy a request."""
