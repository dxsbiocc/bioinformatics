#!/usr/bin/env python3
"""Stdio entrypoint for the Bioinformatics EFO MCP server."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.efo.client import EfoClient, EfoConfig
from mcp.efo.errors import EfoError, McpError
from mcp.efo.tools import TOOL_HANDLERS, tool_definitions
from mcp.rpc import McpServer, error_response, internal_error_response
from mcp.rpc import serve_stdio as _serve_stdio


class EfoMcpServer(McpServer):
    def __init__(self, client: EfoClient | None = None) -> None:
        super().__init__(
            client=client or EfoClient(),
            tool_handlers=TOOL_HANDLERS,
            tool_definitions=tool_definitions,
            server_name="bioinformatics-efo",
        )


def serve_stdio(server: EfoMcpServer | None = None) -> None:
    _serve_stdio(server or EfoMcpServer(), domain_errors=EfoError, service_label="EFO")


__all__ = [
    "EfoClient",
    "EfoConfig",
    "EfoError",
    "EfoMcpServer",
    "McpError",
    "TOOL_HANDLERS",
    "error_response",
    "internal_error_response",
    "serve_stdio",
    "tool_definitions",
]


if __name__ == "__main__":
    serve_stdio()

