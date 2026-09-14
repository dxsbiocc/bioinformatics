"""ClinVar MCP exceptions."""

from __future__ import annotations

from mcp.http_client import UpstreamError
from mcp.rpc import McpError

__all__ = ["McpError", "ClinvarError"]


class ClinvarError(UpstreamError):
    """Raised for ClinVar API and normalization failures."""
