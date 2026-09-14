#!/usr/bin/env python3
"""Stdio entrypoint for the Bioinformatics ClinVar MCP server."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.clinvar.client import ClinvarClient, ClinvarConfig
from mcp.clinvar.errors import ClinvarError, McpError
from mcp.clinvar.tools import TOOL_HANDLERS, tool_definitions
from mcp.rpc import McpServer, error_response, internal_error_response
from mcp.rpc import serve_stdio as _serve_stdio


class ClinvarMcpServer(McpServer):
    def __init__(self, client: ClinvarClient | None = None) -> None:
        super().__init__(
            client=client or ClinvarClient(),
            tool_handlers=TOOL_HANDLERS,
            tool_definitions=tool_definitions,
            server_name="bioinformatics-clinvar",
        )


def serve_stdio(server: ClinvarMcpServer | None = None) -> None:
    _serve_stdio(server or ClinvarMcpServer(), domain_errors=ClinvarError, service_label="ClinVar")


__all__ = [
    "ClinvarClient",
    "ClinvarConfig",
    "ClinvarError",
    "ClinvarMcpServer",
    "McpError",
    "TOOL_HANDLERS",
    "error_response",
    "internal_error_response",
    "serve_stdio",
    "tool_definitions",
]


if __name__ == "__main__":
    serve_stdio()

