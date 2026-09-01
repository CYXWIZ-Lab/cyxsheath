"""Bounded authenticated HTTP proxy from CyxCode Docker to loopback LM Studio."""

from __future__ import annotations

from dataclasses import dataclass
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import re
import secrets
import threading


ALLOWED_PATHS = frozenset({"/v1/models", "/v1/chat/completions"})


class LocalProxyError(ValueError):
    """Raised when the bounded proxy cannot be configured safely."""


@dataclass(frozen=True, slots=True)
class ProxyConfig:
    token: str
    listen_host: str = "0.0.0.0"
    listen_port: int = 1235
    upstream_host: str = "127.0.0.1"
    upstream_port: int = 1234
    timeout_seconds: int = 600
    maximum_request_bytes: int = 8 * 1024 * 1024
    maximum_response_bytes: int = 8 * 1024 * 1024

    def __post_init__(self) -> None:
        if re.fullmatch(r"[0-9a-f]{64}", self.token) is None:
            raise LocalProxyError("proxy token must be 256-bit lowercase hex")
        if self.upstream_host != "127.0.0.1":
            raise LocalProxyError("upstream must be loopback")
        if not isinstance(self.listen_host, str) or not self.listen_host:
            raise LocalProxyError("listen host invalid")
        if (
            isinstance(self.listen_port, bool)
            or not isinstance(self.listen_port, int)
            or not 0 <= self.listen_port <= 65535
        ):
            raise LocalProxyError("listen port invalid")
        if (
            isinstance(self.upstream_port, bool)
            or not isinstance(self.upstream_port, int)
            or not 1 <= self.upstream_port <= 65535
        ):
            raise LocalProxyError("upstream port invalid")
        for name, value, maximum in (
            ("timeout", self.timeout_seconds, 900),
            ("request bound", self.maximum_request_bytes, 8 * 1024 * 1024),
            ("response bound", self.maximum_response_bytes, 8 * 1024 * 1024),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
                raise LocalProxyError(f"{name} invalid")


@dataclass(frozen=True, slots=True)
class ProxyMetrics:
    accepted_requests: int
    denied_requests: int
    request_bytes: int
    response_bytes: int


class LocalModelProxy:
    """Own one short-lived proxy thread and expose aggregate observations only."""

    def __init__(self, config: ProxyConfig) -> None:
        if not isinstance(config, ProxyConfig):
            raise LocalProxyError("proxy config invalid")
        self._config = config
        self._lock = threading.Lock()
        self._accepted = 0
        self._denied = 0
        self._request_bytes = 0
        self._response_bytes = 0
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def address(self) -> tuple[str, int]:
        if self._server is None:
            raise LocalProxyError("proxy not started")
        host, port = self._server.server_address[:2]
        return str(host), int(port)

    @property
    def configuration(self) -> ProxyConfig:
        return self._config

    @property
    def metrics(self) -> ProxyMetrics:
        with self._lock:
            return ProxyMetrics(
                self._accepted,
                self._denied,
                self._request_bytes,
                self._response_bytes,
            )

    def _record_denied(self) -> None:
        with self._lock:
            self._denied += 1

    def _record_accepted(self, request_bytes: int, response_bytes: int) -> None:
        with self._lock:
            self._accepted += 1
            self._request_bytes += request_bytes
            self._response_bytes += response_bytes

    def start(self) -> None:
        if self._server is not None:
            raise LocalProxyError("proxy already started")
        owner = self
        config = self._config

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, _format: str, *args: object) -> None:
                return

            def _deny(self, status: int) -> None:
                owner._record_denied()
                self.send_response(status)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def _handle(self) -> None:
                path = self.path.partition("?")[0]
                if path not in ALLOWED_PATHS:
                    self._deny(404)
                    return
                supplied = self.headers.get("Authorization", "")
                if not secrets.compare_digest(supplied, f"Bearer {config.token}"):
                    self._deny(401)
                    return
                if self.command not in ("GET", "POST"):
                    self._deny(405)
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                except ValueError:
                    self._deny(400)
                    return
                if length < 0 or length > config.maximum_request_bytes:
                    self._deny(413)
                    return
                body = self.rfile.read(length) if length else b""
                headers = {"Accept": self.headers.get("Accept", "application/json")}
                if self.headers.get("Content-Type"):
                    headers["Content-Type"] = self.headers["Content-Type"]
                connection = http.client.HTTPConnection(
                    config.upstream_host,
                    config.upstream_port,
                    timeout=config.timeout_seconds,
                )
                try:
                    connection.request(self.command, self.path, body=body, headers=headers)
                    response = connection.getresponse()
                    payload = response.read(config.maximum_response_bytes + 1)
                    if len(payload) > config.maximum_response_bytes:
                        self._deny(502)
                        return
                    self.send_response(response.status)
                    content_type = response.getheader("Content-Type")
                    if content_type:
                        self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    owner._record_accepted(len(body), len(payload))
                except (OSError, http.client.HTTPException):
                    self._deny(502)
                finally:
                    connection.close()

            do_GET = _handle
            do_POST = _handle

        try:
            self._server = ThreadingHTTPServer((config.listen_host, config.listen_port), Handler)
        except OSError as error:
            raise LocalProxyError("proxy bind failed") from error
        self._server.daemon_threads = True
        self._thread = threading.Thread(target=self._server.serve_forever, name="phase6-local-proxy", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        server, thread = self._server, self._thread
        self._server = None
        self._thread = None
        if server is None:
            return
        server.shutdown()
        server.server_close()
        if thread is not None:
            thread.join(timeout=5)
            if thread.is_alive():
                raise LocalProxyError("proxy thread retained")

    def __enter__(self) -> LocalModelProxy:
        self.start()
        return self

    def __exit__(self, _kind, _value, _traceback) -> None:
        self.stop()


def production_proxy(token: str) -> LocalModelProxy:
    return LocalModelProxy(ProxyConfig(token=token))
