"""Error types used at the MCP and UniProt boundaries."""

from __future__ import annotations

from mcp.http_client import UpstreamError
from mcp.rpc import McpError

__all__ = ["McpError", "UniProtError"]


class UniProtError(UpstreamError):
    """Raised when a UniProt request fails or returns malformed data."""
