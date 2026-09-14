#!/usr/bin/env python3
"""Stdio entrypoint for the Bioinformatics STRING MCP server."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.rpc import McpServer, error_response, internal_error_response
from mcp.rpc import serve_stdio as _serve_stdio
from mcp.stringdb.client import StringDbClient, StringDbConfig
from mcp.stringdb.errors import McpError, StringDbError
from mcp.stringdb.tools import TOOL_HANDLERS, tool_definitions


class StringDbMcpServer(McpServer):
    def __init__(self, client: StringDbClient | None = None) -> None:
        super().__init__(
            client=client or StringDbClient(),
            tool_handlers=TOOL_HANDLERS,
            tool_definitions=tool_definitions,
            server_name="bioinformatics-string",
        )


def serve_stdio(server: StringDbMcpServer | None = None) -> None:
    _serve_stdio(server or StringDbMcpServer(), domain_errors=StringDbError, service_label="STRING")


__all__ = [
    "McpError",
    "StringDbClient",
    "StringDbConfig",
    "StringDbError",
    "StringDbMcpServer",
    "TOOL_HANDLERS",
    "error_response",
    "internal_error_response",
    "serve_stdio",
    "tool_definitions",
]


if __name__ == "__main__":
    serve_stdio()

