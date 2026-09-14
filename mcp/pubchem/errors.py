"""Error types for the PubChem MCP server."""

from __future__ import annotations

from mcp.http_client import UpstreamError
from mcp.rpc import McpError

__all__ = ["McpError", "PubChemError"]


class PubChemError(UpstreamError):
    """Raised when a PubChem request cannot be completed."""
