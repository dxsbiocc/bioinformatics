"""Error types used at the MCP and NCBI boundaries."""

from __future__ import annotations

from mcp.http_client import UpstreamError
from mcp.rpc import McpError

__all__ = ["McpError", "NcbiError"]


class NcbiError(UpstreamError):
    """Raised when an NCBI request fails or returns malformed data."""
