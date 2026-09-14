#!/usr/bin/env python3
"""Stdio entrypoint for the Bioinformatics KEGG MCP server."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.kegg.client import KeggClient, KeggConfig
from mcp.kegg.errors import KeggError, McpError
from mcp.kegg.tools import TOOL_HANDLERS, tool_definitions
from mcp.rpc import McpServer, error_response, internal_error_response
from mcp.rpc import serve_stdio as _serve_stdio


class KeggMcpServer(McpServer):
    def __init__(self, client: KeggClient | None = None) -> None:
        super().__init__(
            client=client or KeggClient(),
            tool_handlers=TOOL_HANDLERS,
            tool_definitions=tool_definitions,
            server_name="bioinformatics-kegg",
        )


def serve_stdio(server: KeggMcpServer | None = None) -> None:
    _serve_stdio(server or KeggMcpServer(), domain_errors=KeggError, service_label="KEGG")


__all__ = [
    "KeggClient",
    "KeggConfig",
    "KeggError",
    "KeggMcpServer",
    "McpError",
    "TOOL_HANDLERS",
    "error_response",
    "internal_error_response",
    "serve_stdio",
    "tool_definitions",
]


if __name__ == "__main__":
    serve_stdio()

