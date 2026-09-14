"""Error types for the GWAS Catalog MCP server."""

from __future__ import annotations

from mcp.http_client import UpstreamError
from mcp.rpc import McpError

__all__ = ["McpError", "GwasError"]


class GwasError(UpstreamError):
    """Raised when a GWAS Catalog request cannot be completed."""
