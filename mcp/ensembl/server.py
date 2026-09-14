#!/usr/bin/env python3
"""Stdio entrypoint for the Bioinformatics Ensembl MCP server."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.ensembl.client import EnsemblClient, EnsemblConfig
from mcp.ensembl.errors import EnsemblError, McpError
from mcp.ensembl.tools import TOOL_HANDLERS, tool_definitions
from mcp.rpc import McpServer, error_response, internal_error_response
from mcp.rpc import serve_stdio as _serve_stdio


class EnsemblMcpServer(McpServer):
    def __init__(self, client: EnsemblClient | None = None) -> None:
        super().__init__(
            client=client or EnsemblClient(),
            tool_handlers=TOOL_HANDLERS,
            tool_definitions=tool_definitions,
            server_name="bioinformatics-ensembl",
        )


def serve_stdio(server: EnsemblMcpServer | None = None) -> None:
    _serve_stdio(server or EnsemblMcpServer(), domain_errors=EnsemblError, service_label="Ensembl")


__all__ = [
    "EnsemblClient",
    "EnsemblConfig",
    "EnsemblError",
    "EnsemblMcpServer",
    "McpError",
    "TOOL_HANDLERS",
    "error_response",
    "internal_error_response",
    "serve_stdio",
    "tool_definitions",
]


if __name__ == "__main__":
    serve_stdio()

