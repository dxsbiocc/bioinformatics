#!/usr/bin/env python3
"""Stdio entrypoint for the Bioinformatics ENCODE MCP server."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.encode.client import EncodeClient, EncodeConfig
from mcp.encode.errors import EncodeError, McpError
from mcp.encode.tools import TOOL_HANDLERS, tool_definitions
from mcp.rpc import McpServer, error_response, internal_error_response
from mcp.rpc import serve_stdio as _serve_stdio


class EncodeMcpServer(McpServer):
    def __init__(self, client: EncodeClient | None = None) -> None:
        super().__init__(
            client=client or EncodeClient(),
            tool_handlers=TOOL_HANDLERS,
            tool_definitions=tool_definitions,
            server_name="bioinformatics-encode",
        )


def serve_stdio(server: EncodeMcpServer | None = None) -> None:
    _serve_stdio(server or EncodeMcpServer(), domain_errors=EncodeError, service_label="ENCODE")


__all__ = [
    "EncodeClient",
    "EncodeConfig",
    "EncodeError",
    "EncodeMcpServer",
    "McpError",
    "TOOL_HANDLERS",
    "error_response",
    "internal_error_response",
    "serve_stdio",
    "tool_definitions",
]


if __name__ == "__main__":
    serve_stdio()

