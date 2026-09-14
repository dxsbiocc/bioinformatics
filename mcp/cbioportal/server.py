#!/usr/bin/env python3
"""Stdio entrypoint for the Bioinformatics cBioPortal MCP server."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.cbioportal.client import CbioPortalClient, CbioPortalConfig
from mcp.cbioportal.errors import CbioPortalError, McpError
from mcp.cbioportal.tools import TOOL_HANDLERS, tool_definitions
from mcp.rpc import McpServer, error_response, internal_error_response
from mcp.rpc import serve_stdio as _serve_stdio


class CbioPortalMcpServer(McpServer):
    def __init__(self, client: CbioPortalClient | None = None) -> None:
        super().__init__(
            client=client or CbioPortalClient(),
            tool_handlers=TOOL_HANDLERS,
            tool_definitions=tool_definitions,
            server_name="bioinformatics-cbioportal",
        )


def serve_stdio(server: CbioPortalMcpServer | None = None) -> None:
    _serve_stdio(server or CbioPortalMcpServer(), domain_errors=CbioPortalError, service_label="cBioPortal")


__all__ = [
    "CbioPortalClient",
    "CbioPortalConfig",
    "CbioPortalError",
    "CbioPortalMcpServer",
    "McpError",
    "TOOL_HANDLERS",
    "error_response",
    "internal_error_response",
    "serve_stdio",
    "tool_definitions",
]


if __name__ == "__main__":
    serve_stdio()

