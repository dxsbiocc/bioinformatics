"""ChEBI MCP errors."""

from __future__ import annotations

from mcp.http_client import UpstreamError
from mcp.rpc import McpError

__all__ = ["McpError", "ChebiError"]


class ChebiError(UpstreamError):
    """Raised when ChEBI cannot return usable data."""
