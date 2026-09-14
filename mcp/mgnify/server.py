#!/usr/bin/env python3
"""Stdio entrypoint for the Bioinformatics MGnify MCP server."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.mgnify.client import MgnifyClient, MgnifyConfig
from mcp.mgnify.errors import McpError, MgnifyError
from mcp.mgnify.tools import TOOL_HANDLERS, tool_definitions
from mcp.rpc import McpServer, error_response, internal_error_response
from mcp.rpc import serve_stdio as _serve_stdio


class MgnifyMcpServer(McpServer):
    def __init__(self, client: MgnifyClient | None = None) -> None:
        super().__init__(
            client=client or MgnifyClient(),
            tool_handlers=TOOL_HANDLERS,
            tool_definitions=tool_definitions,
            server_name="bioinformatics-mgnify",
        )


def serve_stdio(server: MgnifyMcpServer | None = None) -> None:
    _serve_stdio(server or MgnifyMcpServer(), domain_errors=MgnifyError, service_label="MGnify")


__all__ = [
    "MgnifyClient",
    "MgnifyConfig",
    "MgnifyError",
    "MgnifyMcpServer",
    "McpError",
    "TOOL_HANDLERS",
    "error_response",
    "internal_error_response",
    "serve_stdio",
    "tool_definitions",
]


if __name__ == "__main__":
    serve_stdio()

