#!/usr/bin/env python3
"""Stdio entrypoint for the Bioinformatics HMDB MCP server."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.hmdb.client import HmdbClient, HmdbConfig
from mcp.hmdb.errors import HmdbError, McpError
from mcp.hmdb.tools import TOOL_HANDLERS, tool_definitions
from mcp.rpc import McpServer, error_response, internal_error_response
from mcp.rpc import serve_stdio as _serve_stdio


class HmdbMcpServer(McpServer):
    def __init__(self, client: HmdbClient | None = None) -> None:
        super().__init__(
            client=client or HmdbClient(),
            tool_handlers=TOOL_HANDLERS,
            tool_definitions=tool_definitions,
            server_name="bioinformatics-hmdb",
        )


def serve_stdio(server: HmdbMcpServer | None = None) -> None:
    _serve_stdio(server or HmdbMcpServer(), domain_errors=HmdbError, service_label="HMDB")


__all__ = [
    "HmdbClient",
    "HmdbConfig",
    "HmdbError",
    "HmdbMcpServer",
    "McpError",
    "TOOL_HANDLERS",
    "error_response",
    "internal_error_response",
    "serve_stdio",
    "tool_definitions",
]


if __name__ == "__main__":
    serve_stdio()

