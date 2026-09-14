#!/usr/bin/env python3
"""Stdio entrypoint for the Bioinformatics RCSB PDB MCP server."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.rcsb.client import RcsbClient, RcsbConfig
from mcp.rcsb.errors import McpError, RcsbError
from mcp.rcsb.tools import TOOL_HANDLERS, tool_definitions
from mcp.rpc import McpServer, error_response, internal_error_response
from mcp.rpc import serve_stdio as _serve_stdio


class RcsbMcpServer(McpServer):
    def __init__(self, client: RcsbClient | None = None) -> None:
        super().__init__(
            client=client or RcsbClient(),
            tool_handlers=TOOL_HANDLERS,
            tool_definitions=tool_definitions,
            server_name="bioinformatics-rcsb",
        )


def serve_stdio(server: RcsbMcpServer | None = None) -> None:
    _serve_stdio(server or RcsbMcpServer(), domain_errors=RcsbError, service_label="RCSB")


__all__ = [
    "McpError",
    "RcsbClient",
    "RcsbConfig",
    "RcsbError",
    "RcsbMcpServer",
    "TOOL_HANDLERS",
    "error_response",
    "internal_error_response",
    "serve_stdio",
    "tool_definitions",
]


if __name__ == "__main__":
    serve_stdio()

