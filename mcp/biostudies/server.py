#!/usr/bin/env python3
"""Stdio entrypoint for the Bioinformatics BioStudies MCP server."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.biostudies.client import BioStudiesClient, BioStudiesConfig
from mcp.biostudies.errors import BioStudiesError, McpError
from mcp.biostudies.tools import TOOL_HANDLERS, tool_definitions
from mcp.rpc import McpServer, error_response, internal_error_response
from mcp.rpc import serve_stdio as _serve_stdio


class BioStudiesMcpServer(McpServer):
    def __init__(self, client: BioStudiesClient | None = None) -> None:
        super().__init__(
            client=client or BioStudiesClient(),
            tool_handlers=TOOL_HANDLERS,
            tool_definitions=tool_definitions,
            server_name="bioinformatics-biostudies",
        )


def serve_stdio(server: BioStudiesMcpServer | None = None) -> None:
    _serve_stdio(server or BioStudiesMcpServer(), domain_errors=BioStudiesError, service_label="BioStudies")


__all__ = [
    "BioStudiesClient",
    "BioStudiesConfig",
    "BioStudiesError",
    "BioStudiesMcpServer",
    "McpError",
    "TOOL_HANDLERS",
    "error_response",
    "internal_error_response",
    "serve_stdio",
    "tool_definitions",
]


if __name__ == "__main__":
    serve_stdio()
