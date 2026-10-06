"""WO-P1-596: MON-1 read-only local Monitor API (stdlib, loopback-only).

Observability transport only. Every request is authenticated fail-closed:
a per-boot random bearer token (never logged, never in any response),
Origin absent-or-equal to the local origin (CSRF), and an exact
``Host: 127.0.0.1:<port>`` header (DNS-rebinding). GET-only; no mutation
endpoints of any kind; ACT-1 command gateway is separate P8 scope. The API
holds no authority, performs no writes, and a monitor restart never
disturbs control truth — views come from one injected provider call per
snapshot, degrading to typed 503 when the provider fails.
"""
from __future__ import annotations

import hmac
import json
import secrets
import socket
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable

from .monitor_projection import bounded_stream_queue

__all__ = ["MonitorApiConfig", "MonitorApiServer", "MonitorApiError"]

_MAX_PATH_CHARS = 256
_MAX_BODY_BYTES = 1 << 20


class MonitorApiError(RuntimeError):
    """Typed configuration/lifecycle rejection (code-only)."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class MonitorApiConfig:
    host: str = "127.0.0.1"
    port: int = 0  # 0 = ephemeral, bound only on start()
    poll_seconds: float = 0.5
    stream_queue_bound: int = 64

    def __post_init__(self) -> None:
        if self.host not in ("127.0.0.1", "localhost"):
            raise MonitorApiError("MONITOR_HOST_MUST_BE_LOOPBACK")
        if type(self.port) is not int or not 0 <= self.port < 65536:
            raise MonitorApiError("MONITOR_PORT_INVALID")
        if (type(self.poll_seconds) not in (int, float)
                or not 0 < self.poll_seconds <= 60):
            raise MonitorApiError("MONITOR_POLL_INVALID")
        if (type(self.stream_queue_bound) is not int
                or not 1 <= self.stream_queue_bound <= 256):
            raise MonitorApiError("MONITOR_QUEUE_BOUND_INVALID")


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "A-SundayMonitor/1"
    sys_version = ""

    def log_message(self, format, *args):  # noqa: A002 - stdlib signature
        return  # never log tokens/paths

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _authorize(self) -> str | None:
        monitor = self.server.monitor  # type: ignore[attr-defined]
        host_header = self.headers.get("Host", "")
        if host_header != f"127.0.0.1:{monitor.port}":
            return "HOST"
        origin = self.headers.get("Origin")
        if origin is not None and origin != monitor.allowed_origin:
            return "ORIGIN"
        authorization = self.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return "TOKEN"
        candidate = authorization[len("Bearer "):].encode("utf-8", "replace")
        if not hmac.compare_digest(candidate, monitor._token_bytes):
            return "TOKEN"
        return None

    def _authorized_json(self, path: str) -> None:
        monitor = self.server.monitor  # type: ignore[attr-defined]
        if len(path) > _MAX_PATH_CHARS or "%" in path:
            self._send_json(404, {"error": "MONITOR_NOT_FOUND"})
            return
        if path == "/healthz":
            self._send_json(200, {"status": "ok"})
            return
        if path == "/snapshot":
            try:
                views = monitor.provider()
            except Exception:
                self._send_json(503, {"error": "MONITOR_PROJECTION_UNAVAILABLE"})
                return
            self._send_json(200, views)
            return
        if path == "/stream":
            self._stream()
            return
        self._send_json(404, {"error": "MONITOR_NOT_FOUND"})

    def _stream(self) -> None:
        monitor = self.server.monitor  # type: ignore[attr-defined]
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        while not monitor._stop.is_set():
            try:
                views = monitor.provider()
            except Exception:
                views = {"error": "MONITOR_PROJECTION_UNAVAILABLE"}
            monitor._offer(views)
            while monitor._stream_queue:
                frame = dict(monitor._stream_queue.popleft())
                frame["monitor_stream_degraded"] = monitor._stream_degraded
                try:
                    self.wfile.write(
                        (json.dumps(frame)[:_MAX_BODY_BYTES] + "\n").encode("utf-8"))
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, OSError):
                    return  # client disconnect ends the stream; no authority touched
            monitor._stream_degraded = False
            monitor._stop.wait(monitor.config.poll_seconds)

    def do_GET(self):  # noqa: N802 - stdlib signature
        gate = self._authorize()
        if gate is not None:
            # Fail closed with a typed gate name; never echo the token.
            self._send_json(403, {"error": "MONITOR_FORBIDDEN", "gate": gate})
            return
        self._authorized_json(self.path.split("?", 1)[0])

    def _read_only(self):  # POST/PUT/DELETE/PATCH share one typed denial
        gate = self._authorize()
        if gate is not None:
            self._send_json(403, {"error": "MONITOR_FORBIDDEN", "gate": gate})
            return
        self._send_json(405, {"error": "MONITOR_READ_ONLY"})

    do_POST = _read_only
    do_PUT = _read_only
    do_DELETE = _read_only
    do_PATCH = _read_only


class MonitorApiServer:
    """Loopback-only read-only monitor; inert until start() (default OFF)."""

    def __init__(self, provider: Callable[[], dict], config: MonitorApiConfig):
        if not callable(provider):
            raise MonitorApiError("MONITOR_PROVIDER_INVALID")
        if not isinstance(config, MonitorApiConfig):
            raise MonitorApiError("MONITOR_CONFIG_INVALID")
        if config.host != "127.0.0.1" and config.host != "localhost":
            raise MonitorApiError("MONITOR_HOST_MUST_BE_LOOPBACK")
        if type(config.port) is not int or not 0 <= config.port < 65536:
            raise MonitorApiError("MONITOR_PORT_INVALID")
        self.provider = provider
        self.config = config
        self._token = secrets.token_urlsafe(32)
        self._token_bytes = self._token.encode("utf-8")
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._stream_queue = bounded_stream_queue(config.stream_queue_bound)
        self._stream_degraded = False

    @property
    def port(self) -> int | None:
        return self._httpd.server_address[1] if self._httpd is not None else None

    @property
    def token(self) -> str:
        return self._token

    @property
    def allowed_origin(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def _offer(self, views: dict) -> None:
        """Bounded drop-oldest stream feed; overflow marks the next frame."""
        if len(self._stream_queue) == self._stream_queue.maxlen:
            self._stream_degraded = True
        self._stream_queue.append(views)

    def start(self) -> None:
        if self._httpd is not None:
            raise MonitorApiError("MONITOR_ALREADY_RUNNING")
        self._stop.clear()
        httpd = ThreadingHTTPServer((self.config.host, self.config.port), _Handler)
        httpd.daemon_threads = True
        httpd.monitor = self  # type: ignore[attr-defined]
        self._httpd = httpd
        self._thread = threading.Thread(
            target=httpd.serve_forever, kwargs={"poll_interval": 0.05},
            daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        httpd, self._httpd = self._httpd, None
        thread, self._thread = self._thread, None
        if httpd is not None:
            httpd.shutdown()
            httpd.server_close()
        if thread is not None:
            thread.join(timeout=5)
