"""KEGG MCP exceptions."""

from __future__ import annotations

from mcp.http_client import UpstreamError
from mcp.rpc import McpError

__all__ = ["McpError", "KeggError"]


class KeggError(UpstreamError):
    """Raised for KEGG REST errors and normalization failures."""
