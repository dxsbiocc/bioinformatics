#!/usr/bin/env python3
"""Stdio entrypoint for the Bioinformatics GWAS Catalog MCP server."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.gwas.client import GwasClient, GwasConfig
from mcp.gwas.errors import GwasError, McpError
from mcp.gwas.tools import TOOL_HANDLERS, tool_definitions
from mcp.rpc import McpServer, error_response, internal_error_response
from mcp.rpc import serve_stdio as _serve_stdio


class GwasMcpServer(McpServer):
    def __init__(self, client: GwasClient | None = None) -> None:
        super().__init__(
            client=client or GwasClient(),
            tool_handlers=TOOL_HANDLERS,
            tool_definitions=tool_definitions,
            server_name="bioinformatics-gwas",
        )


def serve_stdio(server: GwasMcpServer | None = None) -> None:
    _serve_stdio(server or GwasMcpServer(), domain_errors=GwasError, service_label="GWAS Catalog")


__all__ = [
    "GwasClient",
    "GwasConfig",
    "GwasError",
    "GwasMcpServer",
    "McpError",
    "TOOL_HANDLERS",
    "error_response",
    "internal_error_response",
    "serve_stdio",
    "tool_definitions",
]


if __name__ == "__main__":
    serve_stdio()

