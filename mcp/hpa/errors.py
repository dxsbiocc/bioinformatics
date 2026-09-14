"""Error types for the Human Protein Atlas MCP server."""

from __future__ import annotations

from mcp.http_client import UpstreamError
from mcp.rpc import McpError

__all__ = ["McpError", "HpaError"]


class HpaError(UpstreamError):
    """Raised when Human Protein Atlas cannot satisfy a request."""
