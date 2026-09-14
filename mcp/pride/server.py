#!/usr/bin/env python3
"""Stdio entrypoint for the Bioinformatics PRIDE Archive MCP server."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.pride.client import PrideClient, PrideConfig
from mcp.pride.errors import McpError, PrideError
from mcp.pride.tools import TOOL_HANDLERS, tool_definitions
from mcp.rpc import McpServer, error_response, internal_error_response
from mcp.rpc import serve_stdio as _serve_stdio


class PrideMcpServer(McpServer):
    def __init__(self, client: PrideClient | None = None) -> None:
        super().__init__(
            client=client or PrideClient(),
            tool_handlers=TOOL_HANDLERS,
            tool_definitions=tool_definitions,
            server_name="bioinformatics-pride",
        )


def serve_stdio(server: PrideMcpServer | None = None) -> None:
    _serve_stdio(server or PrideMcpServer(), domain_errors=PrideError, service_label="PRIDE")


__all__ = [
    "McpError",
    "PrideClient",
    "PrideConfig",
    "PrideError",
    "PrideMcpServer",
    "TOOL_HANDLERS",
    "error_response",
    "internal_error_response",
    "serve_stdio",
    "tool_definitions",
]


if __name__ == "__main__":
    serve_stdio()

