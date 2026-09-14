from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr

from mcp import rpc


class FakeClient:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class NoCloseClient:
    """A client with no close() - visualization has no network client."""


class DummyError(Exception):
    pass


def make_server(client: object, *, handlers: dict | None = None) -> rpc.McpServer:
    return rpc.McpServer(
        client=client,
        tool_handlers=handlers or {},
        tool_definitions=lambda: [{"name": "echo"}],
        server_name="bioinformatics-test",
    )


class McpServerTests(unittest.TestCase):
    def test_initialize_returns_latest_protocol_and_server_name(self) -> None:
        server = make_server(FakeClient())
        result = server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        self.assertEqual(result["result"]["protocolVersion"], rpc.LATEST_PROTOCOL_VERSION)
        self.assertEqual(result["result"]["serverInfo"]["name"], "bioinformatics-test")
        self.assertEqual(result["result"]["capabilities"], {"tools": {"listChanged": False}})

    def test_initialize_echoes_supported_requested_version(self) -> None:
        server = make_server(FakeClient())
        result = server.handle(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}}
        )
        self.assertEqual(result["result"]["protocolVersion"], "2024-11-05")

    def test_initialize_falls_back_to_latest_for_unsupported_version(self) -> None:
        server = make_server(FakeClient())
        result = server.handle(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "1999-01-01"}}
        )
        self.assertEqual(result["result"]["protocolVersion"], rpc.LATEST_PROTOCOL_VERSION)

    def test_tools_list_delegates_to_tool_definitions(self) -> None:
        server = make_server(FakeClient())
        result = server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        self.assertEqual(result["result"]["tools"], [{"name": "echo"}])

    def test_notifications_initialized_returns_none(self) -> None:
        server = make_server(FakeClient())
        self.assertIsNone(server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))

    def test_ping_returns_empty_result(self) -> None:
        server = make_server(FakeClient())
        result = server.handle({"jsonrpc": "2.0", "id": 3, "method": "ping"})
        self.assertEqual(result["result"], {})

    def test_tools_call_dispatches_to_handler_with_client(self) -> None:
        client = FakeClient()
        calls = []

        def handler(arguments, passed_client):
            calls.append((arguments, passed_client))
            return {"ok": True}

        server = make_server(client, handlers={"echo": handler})
        result = server.handle(
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "echo", "arguments": {"x": 1}}}
        )
        self.assertEqual(calls, [({"x": 1}, client)])
        self.assertEqual(result["result"]["structuredContent"], {"ok": True})
        self.assertIn('"ok": true', result["result"]["content"][0]["text"])

    def test_tools_call_unknown_tool_raises_mcp_error(self) -> None:
        server = make_server(FakeClient())
        with self.assertRaises(rpc.McpError) as ctx:
            server.handle({"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "nope"}})
        self.assertEqual(ctx.exception.code, -32602)

    def test_tools_call_missing_name_raises_mcp_error(self) -> None:
        server = make_server(FakeClient())
        with self.assertRaises(rpc.McpError):
            server.handle({"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {}})

    def test_wrong_jsonrpc_version_raises_mcp_error(self) -> None:
        server = make_server(FakeClient())
        with self.assertRaises(rpc.McpError) as ctx:
            server.handle({"jsonrpc": "1.0", "id": 1, "method": "ping"})
        self.assertEqual(ctx.exception.code, -32600)

    def test_non_object_params_raises_mcp_error(self) -> None:
        server = make_server(FakeClient())
        with self.assertRaises(rpc.McpError):
            server.handle({"jsonrpc": "2.0", "id": 1, "method": "ping", "params": [1, 2]})

    def test_unknown_method_with_id_raises_method_not_found(self) -> None:
        server = make_server(FakeClient())
        with self.assertRaises(rpc.McpError) as ctx:
            server.handle({"jsonrpc": "2.0", "id": 1, "method": "bogus"})
        self.assertEqual(ctx.exception.code, -32601)

    def test_unknown_method_without_id_returns_none(self) -> None:
        server = make_server(FakeClient())
        self.assertIsNone(server.handle({"jsonrpc": "2.0", "method": "bogus"}))


class ErrorResponseTests(unittest.TestCase):
    def test_error_response_includes_data_when_present(self) -> None:
        payload = rpc.error_response(7, rpc.McpError(-32602, "bad", data={"why": "x"}))
        self.assertEqual(payload, {"jsonrpc": "2.0", "id": 7, "error": {"code": -32602, "message": "bad", "data": {"why": "x"}}})

    def test_error_response_omits_data_when_absent(self) -> None:
        payload = rpc.error_response(None, rpc.McpError(-32600, "bad"))
        self.assertNotIn("data", payload["error"])

    def test_internal_error_response_uses_class_name_when_message_empty(self) -> None:
        payload = rpc.internal_error_response(1, DummyError())
        self.assertEqual(payload["error"]["message"], "DummyError")
        self.assertEqual(payload["error"]["code"], -32603)


class ServeStdioTests(unittest.TestCase):
    def run_stdio(self, server, lines, **kwargs):
        import sys

        stdin = io.StringIO("\n".join(lines) + "\n")
        stdout = io.StringIO()
        old_stdin, old_stdout = sys.stdin, sys.stdout
        sys.stdin, sys.stdout = stdin, stdout
        try:
            rpc.serve_stdio(server, **kwargs)
        finally:
            sys.stdin, sys.stdout = old_stdin, old_stdout
        return [line for line in stdout.getvalue().splitlines() if line]

    def test_processes_request_and_writes_response(self) -> None:
        server = make_server(FakeClient(), handlers={"echo": lambda a, c: {"got": a}})
        out = self.run_stdio(
            server,
            ['{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"echo","arguments":{"a":1}}}'],
            domain_errors=DummyError,
            service_label="Test",
        )
        self.assertEqual(len(out), 1)
        self.assertIn('"got"', out[0])

    def test_skips_blank_lines(self) -> None:
        server = make_server(FakeClient())
        out = self.run_stdio(
            server,
            ["", "   ", '{"jsonrpc":"2.0","id":1,"method":"ping"}'],
            domain_errors=DummyError,
            service_label="Test",
        )
        self.assertEqual(len(out), 1)

    def test_parse_error_reported_without_crashing(self) -> None:
        server = make_server(FakeClient())
        out = self.run_stdio(server, ["not json"], domain_errors=DummyError, service_label="Test")
        self.assertEqual(len(out), 1)
        self.assertIn("Parse error", out[0])

    def test_domain_error_reported_without_stderr_noise(self) -> None:
        def handler(arguments, client):
            raise DummyError("upstream is down")

        server = make_server(FakeClient(), handlers={"echo": handler})
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            out = self.run_stdio(
                server,
                ['{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"echo"}}'],
                domain_errors=DummyError,
                service_label="Test",
            )
        self.assertIn("upstream is down", out[0])
        self.assertEqual(stderr.getvalue(), "")

    def test_unexpected_error_logs_to_stderr(self) -> None:
        def handler(arguments, client):
            raise ValueError("boom")

        server = make_server(FakeClient(), handlers={"echo": handler})
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            out = self.run_stdio(
                server,
                ['{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"echo"}}'],
                domain_errors=DummyError,
                service_label="Test",
            )
        self.assertIn("boom", out[0])
        self.assertIn("Test MCP internal error", stderr.getvalue())

    def test_closes_client_after_stdin_exhausted(self) -> None:
        client = FakeClient()
        server = make_server(client)
        self.run_stdio(server, ['{"jsonrpc":"2.0","id":1,"method":"ping"}'], domain_errors=DummyError, service_label="Test")
        self.assertTrue(client.closed)

    def test_tolerates_client_without_close(self) -> None:
        server = make_server(NoCloseClient())
        # Must not raise even though NoCloseClient has no close().
        self.run_stdio(server, ['{"jsonrpc":"2.0","id":1,"method":"ping"}'], domain_errors=DummyError, service_label="Test")


if __name__ == "__main__":
    unittest.main()
