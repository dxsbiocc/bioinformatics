#!/usr/bin/env python3
"""Stdio entrypoint for the Bioinformatics MetaboLights MCP server."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.metabolights.client import MetaboLightsClient, MetaboLightsConfig
from mcp.metabolights.errors import McpError, MetaboLightsError
from mcp.metabolights.tools import TOOL_HANDLERS, tool_definitions
from mcp.rpc import McpServer, error_response, internal_error_response
from mcp.rpc import serve_stdio as _serve_stdio


class MetaboLightsMcpServer(McpServer):
    def __init__(self, client: MetaboLightsClient | None = None) -> None:
        super().__init__(
            client=client or MetaboLightsClient(),
            tool_handlers=TOOL_HANDLERS,
            tool_definitions=tool_definitions,
            server_name="bioinformatics-metabolights",
        )


def serve_stdio(server: MetaboLightsMcpServer | None = None) -> None:
    _serve_stdio(server or MetaboLightsMcpServer(), domain_errors=MetaboLightsError, service_label="MetaboLights")


__all__ = [
    "MetaboLightsClient",
    "MetaboLightsConfig",
    "MetaboLightsError",
    "MetaboLightsMcpServer",
    "McpError",
    "TOOL_HANDLERS",
    "error_response",
    "internal_error_response",
    "serve_stdio",
    "tool_definitions",
]


if __name__ == "__main__":
    serve_stdio()

