#!/usr/bin/env python3
"""Stdio entrypoint for the Bioinformatics QuickGO MCP server."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.quickgo.client import QuickGoClient, QuickGoConfig
from mcp.quickgo.errors import McpError, QuickGoError
from mcp.quickgo.tools import TOOL_HANDLERS, tool_definitions
from mcp.rpc import McpServer, error_response, internal_error_response
from mcp.rpc import serve_stdio as _serve_stdio


class QuickGoMcpServer(McpServer):
    def __init__(self, client: QuickGoClient | None = None) -> None:
        super().__init__(
            client=client or QuickGoClient(),
            tool_handlers=TOOL_HANDLERS,
            tool_definitions=tool_definitions,
            server_name="bioinformatics-quickgo",
        )


def serve_stdio(server: QuickGoMcpServer | None = None) -> None:
    _serve_stdio(server or QuickGoMcpServer(), domain_errors=QuickGoError, service_label="QuickGO")


__all__ = [
    "McpError",
    "QuickGoClient",
    "QuickGoConfig",
    "QuickGoError",
    "QuickGoMcpServer",
    "TOOL_HANDLERS",
    "error_response",
    "internal_error_response",
    "serve_stdio",
    "tool_definitions",
]


if __name__ == "__main__":
    serve_stdio()

