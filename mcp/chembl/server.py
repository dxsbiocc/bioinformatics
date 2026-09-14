#!/usr/bin/env python3
"""Stdio entrypoint for the Bioinformatics ChEMBL MCP server."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.chembl.client import ChemblClient, ChemblConfig
from mcp.chembl.errors import ChemblError, McpError
from mcp.chembl.tools import TOOL_HANDLERS, tool_definitions
from mcp.rpc import McpServer, error_response, internal_error_response
from mcp.rpc import serve_stdio as _serve_stdio


class ChemblMcpServer(McpServer):
    def __init__(self, client: ChemblClient | None = None) -> None:
        super().__init__(
            client=client or ChemblClient(),
            tool_handlers=TOOL_HANDLERS,
            tool_definitions=tool_definitions,
            server_name="bioinformatics-chembl",
        )


def serve_stdio(server: ChemblMcpServer | None = None) -> None:
    _serve_stdio(server or ChemblMcpServer(), domain_errors=ChemblError, service_label="ChEMBL")


__all__ = [
    "ChemblClient",
    "ChemblConfig",
    "ChemblError",
    "ChemblMcpServer",
    "McpError",
    "TOOL_HANDLERS",
    "error_response",
    "internal_error_response",
    "serve_stdio",
    "tool_definitions",
]


if __name__ == "__main__":
    serve_stdio()
