#!/usr/bin/env python3
"""Stdio entrypoint for the Bioinformatics ChEBI MCP server."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.chebi.client import ChebiClient, ChebiConfig
from mcp.chebi.errors import ChebiError, McpError
from mcp.chebi.tools import TOOL_HANDLERS, tool_definitions
from mcp.rpc import McpServer, error_response, internal_error_response
from mcp.rpc import serve_stdio as _serve_stdio


class ChebiMcpServer(McpServer):
    def __init__(self, client: ChebiClient | None = None) -> None:
        super().__init__(
            client=client or ChebiClient(),
            tool_handlers=TOOL_HANDLERS,
            tool_definitions=tool_definitions,
            server_name="bioinformatics-chebi",
        )


def serve_stdio(server: ChebiMcpServer | None = None) -> None:
    _serve_stdio(server or ChebiMcpServer(), domain_errors=ChebiError, service_label="ChEBI")


__all__ = [
    "ChebiClient",
    "ChebiConfig",
    "ChebiError",
    "ChebiMcpServer",
    "McpError",
    "TOOL_HANDLERS",
    "error_response",
    "internal_error_response",
    "serve_stdio",
    "tool_definitions",
]


if __name__ == "__main__":
    serve_stdio()
