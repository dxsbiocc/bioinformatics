"""Error types for the bioRxiv/medRxiv MCP server."""

from __future__ import annotations

from mcp.http_client import UpstreamError
from mcp.rpc import McpError

__all__ = ["McpError", "BioRxivError"]


class BioRxivError(UpstreamError):
    """Raised when bioRxiv/medRxiv cannot satisfy a request."""
