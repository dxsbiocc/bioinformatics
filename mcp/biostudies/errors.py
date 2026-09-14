"""Error types for the BioStudies MCP server."""

from __future__ import annotations

from mcp.http_client import UpstreamError
from mcp.rpc import McpError

__all__ = ["McpError", "BioStudiesError"]


class BioStudiesError(UpstreamError):
    """Raised when BioStudies cannot satisfy a request."""
