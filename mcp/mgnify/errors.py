"""Error types for the MGnify MCP server."""

from __future__ import annotations

from mcp.http_client import UpstreamError
from mcp.rpc import McpError

__all__ = ["McpError", "MgnifyError"]


class MgnifyError(UpstreamError):
    """Raised for upstream MGnify request or parsing failures."""
