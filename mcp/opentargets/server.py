#!/usr/bin/env python3
"""Stdio entrypoint for the Bioinformatics Open Targets MCP server."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.opentargets.client import OpenTargetsClient, OpenTargetsConfig
from mcp.opentargets.errors import McpError, OpenTargetsError
from mcp.opentargets.tools import TOOL_HANDLERS, tool_definitions
from mcp.rpc import McpServer, error_response, internal_error_response
from mcp.rpc import serve_stdio as _serve_stdio


class OpenTargetsMcpServer(McpServer):
    def __init__(self, client: OpenTargetsClient | None = None) -> None:
        super().__init__(
            client=client or OpenTargetsClient(),
            tool_handlers=TOOL_HANDLERS,
            tool_definitions=tool_definitions,
            server_name="bioinformatics-opentargets",
        )


def serve_stdio(server: OpenTargetsMcpServer | None = None) -> None:
    _serve_stdio(server or OpenTargetsMcpServer(), domain_errors=OpenTargetsError, service_label="Open Targets")


__all__ = [
    "McpError",
    "OpenTargetsClient",
    "OpenTargetsConfig",
    "OpenTargetsError",
    "OpenTargetsMcpServer",
    "TOOL_HANDLERS",
    "error_response",
    "internal_error_response",
    "serve_stdio",
    "tool_definitions",
]


if __name__ == "__main__":
    serve_stdio()
