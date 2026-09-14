"""Shared JSON-RPC/MCP stdio scaffolding used by every bundled MCP server.

Every server under mcp/<name>/server.py wired an identical dispatch class
(initialize/tools-list/tools-call handling), error-response builders, and
stdio read loop by hand. This module holds that scaffolding once; each
server.py now just supplies its client, tool registry, and display name.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from typing import Any

JsonObject = dict[str, Any]

JSONRPC_VERSION = "2.0"
LATEST_PROTOCOL_VERSION = "2025-11-25"
SUPPORTED_PROTOCOL_VERSIONS = {
    LATEST_PROTOCOL_VERSION,
    "2025-06-18",
    "2025-03-26",
    "2024-11-05",
    "2024-10-07",
}


class McpError(Exception):
    """JSON-RPC error with an MCP-compatible code."""

    def __init__(self, code: int, message: str, data: Any | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


class McpServer:
    """Generic initialize/tools-list/tools-call dispatcher.

    Each server's XMcpServer class wraps this with a typed constructor
    (`client: XClient | None = None`) so existing call sites and tests that
    construct `module.XMcpServer(client=...)` keep working unchanged.
    """

    def __init__(
        self,
        *,
        client: Any,
        tool_handlers: dict[str, Callable[[JsonObject, Any], JsonObject]],
        tool_definitions: Callable[[], list[JsonObject]],
        server_name: str,
    ) -> None:
        self.client = client
        self.tool_handlers = tool_handlers
        self.tool_definitions = tool_definitions
        self.server_name = server_name

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
            return self._response(request_id, {"tools": self.tool_definitions()})
        if method == "tools/call":
            return self._response(request_id, self._call_tool(params))

        if request_id is None:
            return None
        raise McpError(-32601, f"Method not found: {method}")

    def _initialize(self, params: JsonObject) -> JsonObject:
        requested = str(params.get("protocolVersion") or LATEST_PROTOCOL_VERSION)
        protocol_version = requested if requested in SUPPORTED_PROTOCOL_VERSIONS else LATEST_PROTOCOL_VERSION
        return {
            "protocolVersion": protocol_version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": self.server_name, "version": "0.1.0"},
        }

    def _call_tool(self, params: JsonObject) -> JsonObject:
        name = params.get("name")
        if not isinstance(name, str) or not name:
            raise McpError(-32602, "tools/call params.name is required")
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            raise McpError(-32602, "tools/call params.arguments must be an object")
        handler = self.tool_handlers.get(name)
        if handler is None:
            raise McpError(-32602, f"Tool not found: {name}")

        result = handler(arguments, self.client)
        return {
            "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}],
            "structuredContent": result,
        }

    def _response(self, request_id: Any, result: JsonObject) -> JsonObject:
        return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "result": result}


def error_response(request_id: Any, error: McpError) -> JsonObject:
    payload: JsonObject = {"jsonrpc": JSONRPC_VERSION, "id": request_id, "error": {"code": error.code, "message": error.message}}
    if error.data is not None:
        payload["error"]["data"] = error.data
    return payload


def internal_error_response(request_id: Any, error: Exception) -> JsonObject:
    message = str(error) or error.__class__.__name__
    return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "error": {"code": -32603, "message": message}}


def serve_stdio(
    server: McpServer,
    *,
    domain_errors: type[Exception] | tuple[type[Exception], ...],
    service_label: str,
) -> None:
    """Read JSON-RPC requests from stdin, one per line, until EOF.

    `domain_errors` are the server's own <X>Error class(es): expected,
    already-descriptive failures (e.g. "could not reach the upstream API")
    that are reported to the caller without also being logged to stderr,
    unlike a truly unexpected exception.
    """
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
        except domain_errors as exc:
            response = internal_error_response(request_id, exc)
        except Exception as exc:  # noqa: BLE001 - MCP boundary must not crash.
            print(f"{service_label} MCP internal error: {exc}", file=sys.stderr)
            response = internal_error_response(request_id, exc)

        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()

    close = getattr(server.client, "close", None)
    if callable(close):
        close()
