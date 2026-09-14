#!/usr/bin/env python3
"""Stdio entrypoint for the Bioinformatics CELLxGENE Discover MCP server."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.cellxgene.client import CellxGeneClient, CellxGeneConfig
from mcp.cellxgene.errors import CellxGeneError, McpError
from mcp.cellxgene.tools import TOOL_HANDLERS, tool_definitions
from mcp.rpc import McpServer, error_response, internal_error_response
from mcp.rpc import serve_stdio as _serve_stdio


class CellxGeneMcpServer(McpServer):
    def __init__(self, client: CellxGeneClient | None = None) -> None:
        super().__init__(
            client=client or CellxGeneClient(),
            tool_handlers=TOOL_HANDLERS,
            tool_definitions=tool_definitions,
            server_name="bioinformatics-cellxgene",
        )


def serve_stdio(server: CellxGeneMcpServer | None = None) -> None:
    _serve_stdio(server or CellxGeneMcpServer(), domain_errors=CellxGeneError, service_label="CELLxGENE")


__all__ = [
    "CellxGeneClient",
    "CellxGeneConfig",
    "CellxGeneError",
    "CellxGeneMcpServer",
    "McpError",
    "TOOL_HANDLERS",
    "error_response",
    "internal_error_response",
    "serve_stdio",
    "tool_definitions",
]


if __name__ == "__main__":
    serve_stdio()
