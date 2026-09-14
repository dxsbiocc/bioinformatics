#!/usr/bin/env python3
"""Stdio entrypoint for the Bioinformatics STRING MCP server."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.stringdb.client import StringDbClient, StringDbConfig
from mcp.stringdb.constants import (
    JSONRPC_VERSION,
    LATEST_PROTOCOL_VERSION,
    SUPPORTED_PROTOCOL_VERSIONS,
    JsonObject,
)
from mcp.stringdb.errors import McpError, StringDbError
from mcp.stringdb.tools import TOOL_HANDLERS, tool_definitions


class StringDbMcpServer:
    def __init__(self, client: StringDbClient | None = None) -> None:
        self.client = client or StringDbClient()

    def handle(self, request: JsonObject) -> JsonObject | None:
        if request.get("jsonrpc") != JSONRPC_VERSION:
            raise McpError(-32600, "Request jsonrpc must be '2.0'")
        method = request.get("method")
        request_id = request.get("id")
        params = request.get("params", {})
        if params is None:
            params = {}
        if not isinstance(params, dict):
            raise McpError(-32602, "params must be an object")

        if method == "initialize":
            return self._response(request_id, self._initialize(params))
        if method == "notifications/initialized":
            return None
        if method == "ping":
            return self._response(request_id, {})
        if method == "tools/list":
            return self._response(request_id, {"tools": tool_definitions()})
        if method == "tools/call":
            return self._response(request_id, self._call_tool(params))

        if request_id is None:
            return None
        raise McpError(-32601, f"Method not found: {method}")

    def _initialize(self, params: JsonObject) -> JsonObject:
        requested = str(params.get("protocolVersion") or LATEST_PROTOCOL_VERSION)
        protocol_version = (
            requested if requested in SUPPORTED_PROTOCOL_VERSIONS else LATEST_PROTOCOL_VERSION
        )
        return {
            "protocolVersion": protocol_version,
            "capabilities": {
                "tools": {
                    "listChanged": False,
                },
            },
            "serverInfo": {
                "name": "bioinformatics-string",
                "version": "0.1.0",
            },
        }

    def _call_tool(self, params: JsonObject) -> JsonObject:
        name = params.get("name")
        if not isinstance(name, str) or not name:
            raise McpError(-32602, "tools/call params.name is required")
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            raise McpError(-32602, "tools/call params.arguments must be an object")
        handler = TOOL_HANDLERS.get(name)
        if handler is None:
            raise McpError(-32602, f"Tool not found: {name}")

        result = handler(arguments, self.client)
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, ensure_ascii=False, indent=2),
                }
            ],
            "structuredContent": result,
        }

    def _response(self, request_id: Any, result: JsonObject) -> JsonObject:
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": request_id,
            "result": result,
        }


def error_response(request_id: Any, error: McpError) -> JsonObject:
    payload: JsonObject = {
        "jsonrpc": JSONRPC_VERSION,
        "id": request_id,
        "error": {
            "code": error.code,
            "message": error.message,
        },
    }
    if error.data is not None:
        payload["error"]["data"] = error.data
    return payload


def internal_error_response(request_id: Any, error: Exception) -> JsonObject:
    message = str(error) or error.__class__.__name__
    return {
        "jsonrpc": JSONRPC_VERSION,
        "id": request_id,
        "error": {
            "code": -32603,
            "message": message,
        },
    }


def serve_stdio(server: StringDbMcpServer | None = None) -> None:
    server = server or StringDbMcpServer()
    for line in sys.stdin:
        if not line.strip():
            continue
        request_id: Any = None
        try:
            request = json.loads(line)
            if not isinstance(request, dict):
                raise McpError(-32600, "Request must be a JSON object")
            request_id = request.get("id")
            response = server.handle(request)
        except json.JSONDecodeError as exc:
            response = error_response(None, McpError(-32700, "Parse error", str(exc)))
        except McpError as exc:
            response = error_response(request_id, exc)
        except Exception as exc:  # noqa: BLE001 - MCP boundary must not crash.
            print(f"STRING MCP internal error: {exc}", file=sys.stderr)
            response = internal_error_response(request_id, exc)

        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()

    server.client.close()


__all__ = [
    "McpError",
    "StringDbClient",
    "StringDbConfig",
    "StringDbError",
    "StringDbMcpServer",
    "TOOL_HANDLERS",
    "error_response",
    "internal_error_response",
    "serve_stdio",
    "tool_definitions",
]


if __name__ == "__main__":
    serve_stdio()

