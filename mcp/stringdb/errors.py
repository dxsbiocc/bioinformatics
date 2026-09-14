"""STRING MCP exceptions."""

from __future__ import annotations

from mcp.http_client import UpstreamError
from mcp.rpc import McpError

__all__ = ["McpError", "StringDbError"]


class StringDbError(UpstreamError):
    """Raised for STRING API and normalization failures."""
