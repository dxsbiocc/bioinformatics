#!/usr/bin/env python3
"""Stdio entrypoint for the Bioinformatics AlphaFold MCP server."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.alphafold.client import AlphaFoldClient, AlphaFoldConfig
from mcp.alphafold.errors import AlphaFoldError, McpError
from mcp.alphafold.tools import TOOL_HANDLERS, tool_definitions
from mcp.rpc import McpServer, error_response, internal_error_response
from mcp.rpc import serve_stdio as _serve_stdio


class AlphaFoldMcpServer(McpServer):
    def __init__(self, client: AlphaFoldClient | None = None) -> None:
        super().__init__(
            client=client or AlphaFoldClient(),
            tool_handlers=TOOL_HANDLERS,
            tool_definitions=tool_definitions,
            server_name="bioinformatics-alphafold",
        )


def serve_stdio(server: AlphaFoldMcpServer | None = None) -> None:
    _serve_stdio(server or AlphaFoldMcpServer(), domain_errors=AlphaFoldError, service_label="AlphaFold")


__all__ = [
    "AlphaFoldClient",
    "AlphaFoldConfig",
    "AlphaFoldError",
    "AlphaFoldMcpServer",
    "McpError",
    "TOOL_HANDLERS",
    "error_response",
    "internal_error_response",
    "serve_stdio",
    "tool_definitions",
]


if __name__ == "__main__":
    serve_stdio()
