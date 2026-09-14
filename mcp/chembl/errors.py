"""Error types for the ChEMBL MCP server."""

from __future__ import annotations

from mcp.http_client import UpstreamError
from mcp.rpc import McpError

__all__ = ["McpError", "ChemblError"]


class ChemblError(UpstreamError):
    """Raised when a ChEMBL request cannot be completed."""
