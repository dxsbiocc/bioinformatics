"""Error types for the MetaboLights MCP server."""

from __future__ import annotations

from mcp.http_client import UpstreamError
from mcp.rpc import McpError

__all__ = ["McpError", "MetaboLightsError"]


class MetaboLightsError(UpstreamError):
    """Raised for upstream MetaboLights request or parsing failures."""
