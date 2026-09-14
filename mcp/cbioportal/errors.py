"""cBioPortal MCP error types."""

from __future__ import annotations

from mcp.http_client import UpstreamError
from mcp.rpc import McpError

__all__ = ["McpError", "CbioPortalError"]


class CbioPortalError(UpstreamError):
    """Raised when cBioPortal retrieval or normalization fails."""
