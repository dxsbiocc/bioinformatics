#!/usr/bin/env python3
"""Stdio entrypoint for the Bioinformatics RNAcentral MCP server."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.rnacentral.client import RnaCentralClient, RnaCentralConfig
from mcp.rnacentral.errors import McpError, RnaCentralError
from mcp.rnacentral.tools import TOOL_HANDLERS, tool_definitions
from mcp.rpc import McpServer, error_response, internal_error_response
from mcp.rpc import serve_stdio as _serve_stdio


class RnaCentralMcpServer(McpServer):
    def __init__(self, client: RnaCentralClient | None = None) -> None:
        super().__init__(
            client=client or RnaCentralClient(),
            tool_handlers=TOOL_HANDLERS,
            tool_definitions=tool_definitions,
            server_name="bioinformatics-rnacentral",
        )


def serve_stdio(server: RnaCentralMcpServer | None = None) -> None:
    _serve_stdio(server or RnaCentralMcpServer(), domain_errors=RnaCentralError, service_label="RNAcentral")


__all__ = [
    "McpError",
    "RnaCentralClient",
    "RnaCentralConfig",
    "RnaCentralError",
    "RnaCentralMcpServer",
    "TOOL_HANDLERS",
    "error_response",
    "internal_error_response",
    "serve_stdio",
    "tool_definitions",
]


if __name__ == "__main__":
    serve_stdio()

