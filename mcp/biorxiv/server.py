#!/usr/bin/env python3
"""Stdio entrypoint for the Bioinformatics bioRxiv/medRxiv MCP server."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.biorxiv.client import BioRxivClient, BioRxivConfig
from mcp.biorxiv.errors import BioRxivError, McpError
from mcp.biorxiv.tools import TOOL_HANDLERS, tool_definitions
from mcp.rpc import McpServer, error_response, internal_error_response
from mcp.rpc import serve_stdio as _serve_stdio


class BioRxivMcpServer(McpServer):
    def __init__(self, client: BioRxivClient | None = None) -> None:
        super().__init__(
            client=client or BioRxivClient(),
            tool_handlers=TOOL_HANDLERS,
            tool_definitions=tool_definitions,
            server_name="bioinformatics-biorxiv",
        )


def serve_stdio(server: BioRxivMcpServer | None = None) -> None:
    _serve_stdio(server or BioRxivMcpServer(), domain_errors=BioRxivError, service_label="bioRxiv")


__all__ = [
    "BioRxivClient",
    "BioRxivConfig",
    "BioRxivError",
    "BioRxivMcpServer",
    "McpError",
    "TOOL_HANDLERS",
    "error_response",
    "internal_error_response",
    "serve_stdio",
    "tool_definitions",
]


if __name__ == "__main__":
    serve_stdio()

