"""Error types for the Open Targets MCP server."""

from __future__ import annotations

from mcp.http_client import UpstreamError
from mcp.rpc import McpError

__all__ = ["McpError", "OpenTargetsError"]


class OpenTargetsError(UpstreamError):
    """Raised when an Open Targets request cannot be completed."""
