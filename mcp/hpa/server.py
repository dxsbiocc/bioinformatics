#!/usr/bin/env python3
"""Stdio entrypoint for the Bioinformatics Human Protein Atlas MCP server."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.hpa.client import HpaClient, HpaConfig
from mcp.hpa.errors import HpaError, McpError
from mcp.hpa.tools import TOOL_HANDLERS, tool_definitions
from mcp.rpc import McpServer, error_response, internal_error_response
from mcp.rpc import serve_stdio as _serve_stdio


class HpaMcpServer(McpServer):
    def __init__(self, client: HpaClient | None = None) -> None:
        super().__init__(
            client=client or HpaClient(),
            tool_handlers=TOOL_HANDLERS,
            tool_definitions=tool_definitions,
            server_name="bioinformatics-hpa",
        )


def serve_stdio(server: HpaMcpServer | None = None) -> None:
    _serve_stdio(server or HpaMcpServer(), domain_errors=HpaError, service_label="HPA")


__all__ = [
    "HpaClient",
    "HpaConfig",
    "HpaError",
    "HpaMcpServer",
    "McpError",
    "TOOL_HANDLERS",
    "error_response",
    "internal_error_response",
    "serve_stdio",
    "tool_definitions",
]


if __name__ == "__main__":
    serve_stdio()
