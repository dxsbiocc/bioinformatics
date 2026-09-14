"""Reactome MCP exceptions."""

from __future__ import annotations

from mcp.http_client import UpstreamError
from mcp.rpc import McpError

__all__ = ["McpError", "ReactomeError"]


class ReactomeError(UpstreamError):
    """Raised for Reactome API and normalization failures."""
