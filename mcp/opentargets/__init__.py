"""Open Targets MCP server package."""

from .client import OpenTargetsClient, OpenTargetsConfig
from .errors import McpError, OpenTargetsError
from .server import OpenTargetsMcpServer

__all__ = [
    "McpError",
    "OpenTargetsClient",
    "OpenTargetsConfig",
    "OpenTargetsError",
    "OpenTargetsMcpServer",
]
