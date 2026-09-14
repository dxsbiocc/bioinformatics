"""Error types for the CELLxGENE Discover MCP server."""

from __future__ import annotations

from mcp.http_client import UpstreamError
from mcp.rpc import McpError

__all__ = ["McpError", "CellxGeneError"]


class CellxGeneError(UpstreamError):
    """Raised when CELLxGENE Discover cannot satisfy a request."""
