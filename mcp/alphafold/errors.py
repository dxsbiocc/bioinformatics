"""AlphaFold MCP exceptions."""

from __future__ import annotations

from mcp.http_client import UpstreamError
from mcp.rpc import McpError

__all__ = ["McpError", "AlphaFoldError"]


class AlphaFoldError(UpstreamError):
    """Raised for AlphaFold API and normalization failures."""
