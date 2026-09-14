from __future__ import annotations

import unittest

import httpx

from mcp.http_client import PacedHttpClient, UpstreamError


class DemoError(UpstreamError):
    pass


def make_client(handler, **kwargs) -> PacedHttpClient:
    return PacedHttpClient(
        error_class=DemoError,
        service_name="Demo",
        requests_per_second=1000,  # keep tests fast; throttle tested separately
        sleep=lambda _: None,
        transport=httpx.MockTransport(handler),
        **kwargs,
    )


class UpstreamErrorTests(unittest.TestCase):
    def test_defaults_are_empty_not_none(self) -> None:
        err = DemoError("boom")
        self.assertIsNone(err.status_code)
        self.assertEqual(err.endpoint, "")
        self.assertEqual(err.response_body, "")
        self.assertEqual(err.headers, {})

    def test_carries_supplied_context(self) -> None:
        err = DemoError("boom", status_code=404, endpoint="x", response_body="body", headers={"a": "b"})
        self.assertEqual(err.status_code, 404)
        self.assertEqual(err.endpoint, "x")
        self.assertEqual(err.response_body, "body")
        self.assertEqual(err.headers, {"a": "b"})


class SendSuccessTests(unittest.TestCase):
    def test_returns_text_and_lowercased_headers(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="hello", headers={"X-Custom": "1"})

        client = make_client(handler)
        text, headers = client.send("GET", "https://example.test/x", {"Accept": "text/plain"}, label="x")
        self.assertEqual(text, "hello")
        self.assertEqual(headers["x-custom"], "1")

    def test_sends_method_and_content(self) -> None:
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["method"] = request.method
            seen["content"] = request.read()
            return httpx.Response(200, text="{}")

        client = make_client(handler)
        client.send("POST", "https://example.test/graphql", {"Content-Type": "application/json"}, content=b'{"q":1}', label="graphql")
        self.assertEqual(seen["method"], "POST")
        self.assertEqual(seen["content"], b'{"q":1}')

    def test_closes_and_recreates_underlying_client(self) -> None:
        client = make_client(lambda r: httpx.Response(200, text="ok"))
        client.send("GET", "https://example.test/x", {}, label="x")
        underlying = client._http
        self.assertIsNotNone(underlying)
        client.close()
        self.assertIsNone(client._http)
        client.send("GET", "https://example.test/x", {}, label="x")
        self.assertIsNotNone(client._http)
        self.assertIsNot(client._http, underlying)


class SendHttpStatusErrorTests(unittest.TestCase):
    def test_4xx_raises_immediately_without_retry(self) -> None:
        calls = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(1)
            return httpx.Response(404, text="not found")

        client = make_client(handler, max_retries=3)
        with self.assertRaises(DemoError) as ctx:
            client.send("GET", "https://example.test/x", {}, label="lookup")
        self.assertEqual(len(calls), 1, "a 4xx must not be retried")
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.endpoint, "lookup")
        self.assertIn("not found", ctx.exception.response_body)
        self.assertIn("Demo lookup returned HTTP 404", str(ctx.exception))

    def test_5xx_raises_immediately_without_retry(self) -> None:
        calls = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(1)
            return httpx.Response(500, text="boom")

        client = make_client(handler, max_retries=3)
        with self.assertRaises(DemoError):
            client.send("GET", "https://example.test/x", {}, label="lookup")
        self.assertEqual(len(calls), 1)

    def test_response_headers_preserved_on_status_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(403, text="cf", headers={"cf-mitigated": "challenge"})

        client = make_client(handler)
        with self.assertRaises(DemoError) as ctx:
            client.send("GET", "https://example.test/x", {}, label="x")
        self.assertEqual(ctx.exception.headers.get("cf-mitigated"), "challenge")


class SendRequestErrorTests(unittest.TestCase):
    def test_retries_transport_failures_then_succeeds(self) -> None:
        attempts = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            attempts["n"] += 1
            if attempts["n"] < 3:
                raise httpx.ConnectError("refused", request=request)
            return httpx.Response(200, text="recovered")

        client = make_client(handler, max_retries=2)
        text, _ = client.send("GET", "https://example.test/x", {}, label="x")
        self.assertEqual(text, "recovered")
        self.assertEqual(attempts["n"], 3)

    def test_raises_after_exhausting_retries(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectTimeout("timed out", request=request)

        client = make_client(handler, max_retries=1)
        with self.assertRaises(DemoError) as ctx:
            client.send("GET", "https://example.test/x", {}, label="x")
        self.assertIsNone(ctx.exception.status_code)
        self.assertIn("Could not reach Demo x", str(ctx.exception))


class OpenerTests(unittest.TestCase):
    def test_string_opener_result_wrapped_with_empty_headers(self) -> None:
        client = PacedHttpClient(
            error_class=DemoError,
            service_name="Demo",
            opener=lambda request, timeout: "plain text",
        )
        text, headers = client.send("GET", "https://example.test/x", {}, label="x")
        self.assertEqual(text, "plain text")
        self.assertEqual(headers, {})

    def test_tuple_opener_result_passed_through(self) -> None:
        client = PacedHttpClient(
            error_class=DemoError,
            service_name="Demo",
            opener=lambda request, timeout: ("body", {"x": "y"}),
        )
        text, headers = client.send("GET", "https://example.test/x", {}, label="x")
        self.assertEqual(text, "body")
        self.assertEqual(headers, {"x": "y"})

    def test_opener_bypasses_the_network_entirely(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise AssertionError("network should not be reached when opener is set")

        client = PacedHttpClient(
            error_class=DemoError,
            service_name="Demo",
            opener=lambda request, timeout: "from opener",
            transport=httpx.MockTransport(handler),
        )
        text, _ = client.send("GET", "https://example.test/x", {}, label="x")
        self.assertEqual(text, "from opener")


class ThrottleTests(unittest.TestCase):
    # throttle() reads monotonic() twice per call: once for `now`, once to
    # record `_last_request_at`. Each call below supplies one such pair.
    def test_sleeps_when_called_faster_than_the_configured_rate(self) -> None:
        sleeps = []
        times = iter([10.0, 10.0, 10.1, 10.1])
        client = PacedHttpClient(
            error_class=DemoError,
            service_name="Demo",
            requests_per_second=2,  # minimum interval 0.5s
            sleep=sleeps.append,
            monotonic=lambda: next(times),
        )
        client.throttle()  # far from the t=0 baseline: no sleep
        client.throttle()  # only 0.1s after the previous call: sleeps
        self.assertEqual(len(sleeps), 1)
        self.assertAlmostEqual(sleeps[0], 0.4, places=5)

    def test_does_not_sleep_when_calls_are_already_spaced_out(self) -> None:
        sleeps = []
        times = iter([100.0, 100.0, 110.0, 110.0])
        client = PacedHttpClient(
            error_class=DemoError,
            service_name="Demo",
            requests_per_second=2,
            sleep=sleeps.append,
            monotonic=lambda: next(times),
        )
        client.throttle()
        client.throttle()
        self.assertEqual(sleeps, [])


if __name__ == "__main__":
    unittest.main()
