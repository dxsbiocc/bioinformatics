#!/usr/bin/env python3
"""Stdio entrypoint for the Bioinformatics Reactome MCP server."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.reactome.client import ReactomeClient, ReactomeConfig
from mcp.reactome.errors import McpError, ReactomeError
from mcp.reactome.tools import TOOL_HANDLERS, tool_definitions
from mcp.rpc import McpServer, error_response, internal_error_response
from mcp.rpc import serve_stdio as _serve_stdio


class ReactomeMcpServer(McpServer):
    def __init__(self, client: ReactomeClient | None = None) -> None:
        super().__init__(
            client=client or ReactomeClient(),
            tool_handlers=TOOL_HANDLERS,
            tool_definitions=tool_definitions,
            server_name="bioinformatics-reactome",
        )


def serve_stdio(server: ReactomeMcpServer | None = None) -> None:
    _serve_stdio(server or ReactomeMcpServer(), domain_errors=ReactomeError, service_label="Reactome")


__all__ = [
    "McpError",
    "ReactomeClient",
    "ReactomeConfig",
    "ReactomeError",
    "ReactomeMcpServer",
    "TOOL_HANDLERS",
    "error_response",
    "internal_error_response",
    "serve_stdio",
    "tool_definitions",
]


if __name__ == "__main__":
    serve_stdio()

