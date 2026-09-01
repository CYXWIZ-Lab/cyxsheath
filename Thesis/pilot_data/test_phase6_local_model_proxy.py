from __future__ import annotations

import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import threading
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from phase6_local_model_proxy import LocalModelProxy, LocalProxyError, ProxyConfig, production_proxy


TOKEN = "a" * 64


class Upstream:
    def __init__(self, response: bytes = b'{"ok":true}') -> None:
        self.requests: list[tuple[str, str, bytes, str]] = []
        self.stopped = False
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, _format: str, *args: object) -> None:
                return

            def _handle(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length) if length else b""
                owner.requests.append((self.command, self.path, body, self.headers.get("Authorization", "")))
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)

            do_GET = _handle
            do_POST = _handle

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def port(self) -> int:
        return int(self.server.server_address[1])

    def stop(self) -> None:
        if self.stopped:
            return
        self.stopped = True
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


class LocalModelProxyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.upstream = Upstream()
        self.addCleanup(self.upstream.stop)
        config = ProxyConfig(
            token=TOKEN,
            listen_host="127.0.0.1",
            listen_port=0,
            upstream_port=self.upstream.port,
        )
        self.proxy = LocalModelProxy(config)
        self.proxy.start()
        self.addCleanup(self.proxy.stop)

    def _request(self, method: str, path: str, body: bytes = b"", token: str = TOKEN):
        connection = http.client.HTTPConnection("127.0.0.1", self.proxy.address[1], timeout=5)
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        payload = response.read()
        connection.close()
        return response.status, payload

    def test_authorized_request_is_forwarded_without_authorization(self) -> None:
        status, payload = self._request("POST", "/v1/chat/completions", b'{"model":"fixture"}')
        self.assertEqual(200, status)
        self.assertEqual(b'{"ok":true}', payload)
        self.assertEqual("", self.upstream.requests[0][3])
        self.assertEqual(1, self.proxy.metrics.accepted_requests)

    def test_missing_or_wrong_token_never_reaches_upstream(self) -> None:
        self.assertEqual(401, self._request("GET", "/v1/models", token="b" * 64)[0])
        self.assertEqual([], self.upstream.requests)
        self.assertEqual(1, self.proxy.metrics.denied_requests)

    def test_non_allowlisted_path_is_rejected(self) -> None:
        self.assertEqual(404, self._request("GET", "/api/v1/chat")[0])
        self.assertEqual([], self.upstream.requests)

    def test_request_bound_is_enforced_before_forwarding(self) -> None:
        self.proxy.stop()
        config = ProxyConfig(
            token=TOKEN,
            listen_host="127.0.0.1",
            listen_port=0,
            upstream_port=self.upstream.port,
            maximum_request_bytes=4,
        )
        self.proxy = LocalModelProxy(config)
        self.proxy.start()
        self.addCleanup(self.proxy.stop)
        self.assertEqual(413, self._request("POST", "/v1/chat/completions", b"12345")[0])
        self.assertEqual([], self.upstream.requests)

    def test_response_bound_is_enforced(self) -> None:
        self.proxy.stop()
        self.upstream.stop()
        self.upstream = Upstream(b"12345")
        self.addCleanup(self.upstream.stop)
        config = ProxyConfig(
            token=TOKEN,
            listen_host="127.0.0.1",
            listen_port=0,
            upstream_port=self.upstream.port,
            maximum_response_bytes=4,
        )
        self.proxy = LocalModelProxy(config)
        self.proxy.start()
        self.addCleanup(self.proxy.stop)
        self.assertEqual(502, self._request("GET", "/v1/models")[0])

    def test_production_proxy_has_exact_network_boundary(self) -> None:
        proxy = production_proxy(TOKEN)
        self.assertEqual("0.0.0.0", proxy.configuration.listen_host)
        self.assertEqual(1235, proxy.configuration.listen_port)
        self.assertEqual("127.0.0.1", proxy.configuration.upstream_host)
        self.assertEqual(1234, proxy.configuration.upstream_port)

    def test_invalid_token_is_rejected(self) -> None:
        with self.assertRaisesRegex(LocalProxyError, "256-bit"):
            production_proxy("short")


if __name__ == "__main__":
    unittest.main()
