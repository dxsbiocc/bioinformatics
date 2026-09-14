"""RCSB PDB MCP exceptions."""

from __future__ import annotations

from mcp.http_client import UpstreamError
from mcp.rpc import McpError

__all__ = ["McpError", "RcsbError"]


class RcsbError(UpstreamError):
    """Raised for RCSB API and normalization failures."""
