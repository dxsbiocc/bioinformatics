#!/usr/bin/env python3
"""Stdio entrypoint for the Bioinformatics UniProt MCP server."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.rpc import McpServer, error_response, internal_error_response
from mcp.rpc import serve_stdio as _serve_stdio
from mcp.uniprot.client import UniProtClient, UniProtConfig
from mcp.uniprot.errors import McpError, UniProtError
from mcp.uniprot.tools import TOOL_HANDLERS, tool_definitions


class UniProtMcpServer(McpServer):
    def __init__(self, client: UniProtClient | None = None) -> None:
        super().__init__(
            client=client or UniProtClient(),
            tool_handlers=TOOL_HANDLERS,
            tool_definitions=tool_definitions,
            server_name="bioinformatics-uniprot",
        )


def serve_stdio(server: UniProtMcpServer | None = None) -> None:
    _serve_stdio(server or UniProtMcpServer(), domain_errors=UniProtError, service_label="UniProt")


__all__ = [
    "McpError",
    "TOOL_HANDLERS",
    "UniProtClient",
    "UniProtConfig",
    "UniProtError",
    "UniProtMcpServer",
    "error_response",
    "internal_error_response",
    "serve_stdio",
    "tool_definitions",
]


if __name__ == "__main__":
    serve_stdio()
