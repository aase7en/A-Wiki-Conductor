"""WO-P1-596: MON-1 read-only local Monitor API (stdlib, loopback-only).

Observability transport only. Every request is authenticated fail-closed:
a per-boot random bearer token (never logged, never in any response, hmac
compared), duplicate Host/Origin/Authorization headers rejected before
comparison, Origin absent-or-equal to the local origin (CSRF), and an exact
``Host: 127.0.0.1:<port>`` header (DNS-rebinding). GET-only; no mutation
endpoints of any kind; ACT-1 command gateway is separate P8 scope.

The API holds no authority and performs no writes. Snapshots come from one
injected provider call, fully serialized inside a typed failure boundary
(503 ``MONITOR_PROJECTION_UNAVAILABLE`` on any provider/serialization
failure). Streaming uses a poller thread feeding per-subscriber bounded
drop-oldest queues: a slow consumer's queue overflows (degraded marker on
its own frames) while production and other subscribers continue, and any
frame exceeding the wire bound becomes a complete typed error frame —
never truncated JSON. Accepted connections are tracked with bounded
request lifetimes and force-closed on stop(); a monitor restart never
disturbs control truth, and the server is inert until start() (default OFF).
"""
from __future__ import annotations

import hmac
import json
import secrets
import socket
import threading
from collections import deque
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable

__all__ = ["MonitorApiConfig", "MonitorApiServer", "MonitorApiError"]

_MAX_PATH_CHARS = 256
_MAX_FRAME_BYTES = 262_144
_HANDLER_TIMEOUT_SECONDS = 10


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


class _Subscriber:
    """One stream consumer's bounded drop-oldest feed."""

    __slots__ = ("queue", "degraded")

    def __init__(self, bound: int) -> None:
        self.queue: deque = deque(maxlen=bound)
        self.degraded = False


class _MonitorHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.monitor = None  # type: ignore[attr-defined]
        self._conns: set[socket.socket] = set()
        self._conn_lock = threading.Lock()

    def get_request(self):
        conn, addr = super().get_request()
        with self._conn_lock:
            self._conns.add(conn)
        return conn, addr

    def close_all_connections(self) -> None:
        with self._conn_lock:
            conns = list(self._conns)
            self._conns.clear()
        for conn in conns:
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                conn.close()
            except OSError:
                pass


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "A-SundayMonitor/1"
    sys_version = ""
    # Bounded request lifetime: an incomplete request cannot hold a thread
    # past this window even without stop() (Sol round-1 P1).
    timeout = _HANDLER_TIMEOUT_SECONDS

    def log_message(self, format, *args):  # noqa: A002 - stdlib signature
        return  # never log tokens/paths

    def handle_one_request(self):
        # Forced close on stop() or a dropped client surfaces as
        # ConnectionReset/Timeout inside the stdlib read loop; end the
        # request quietly instead of printing a handler traceback.
        try:
            super().handle_one_request()
        except (ConnectionError, TimeoutError, OSError):
            self.close_connection = True

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_raw_json(self, status: int, body_text: str) -> None:
        body = body_text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _authorize(self) -> str | None:
        monitor = self.server.monitor  # type: ignore[attr-defined]
        # Fail closed on duplicate security headers before any comparison;
        # .get() would only see the first value (Sol round-1 P1).
        for header, gate in (("Host", "HOST_DUPLICATE"),
                             ("Origin", "ORIGIN_DUPLICATE"),
                             ("Authorization", "TOKEN_DUPLICATE")):
            values = self.headers.get_all(header)
            if values is not None and len(values) > 1:
                return gate
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
            # Provider call AND full serialization inside one typed failure
            # boundary; a non-JSON-serializable view is 503, never a
            # traceback (Sol round-1 P2).
            try:
                payload = json.dumps(monitor.provider())
            except Exception:
                self._send_json(503, {"error": "MONITOR_PROJECTION_UNAVAILABLE"})
                return
            self._send_raw_json(200, payload)
            return
        if path == "/stream":
            self._stream()
            return
        self._send_json(404, {"error": "MONITOR_NOT_FOUND"})

    def _stream(self) -> None:
        monitor = self.server.monitor  # type: ignore[attr-defined]
        subscriber = monitor._subscribe()
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            while not monitor._stop.is_set():
                if not subscriber.queue:
                    monitor._stop.wait(0.05)
                    continue
                while subscriber.queue:
                    frame = dict(subscriber.queue.popleft())
                    frame["monitor_stream_degraded"] = subscriber.degraded
                    subscriber.degraded = False
                    try:
                        body = json.dumps(frame)
                    except Exception:
                        body = json.dumps({"error": "MONITOR_FRAME_OVERSIZED"})
                    if len(body) > _MAX_FRAME_BYTES:
                        body = json.dumps({"error": "MONITOR_FRAME_OVERSIZED"})
                    try:
                        self.wfile.write((body + "\n").encode("utf-8"))
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError, OSError):
                        return  # client gone; no authority touched
        finally:
            monitor._unsubscribe(subscriber)

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
    """Loopback-only read-only monitor; inert until start() (default OFF).

    A poller thread produces one provider snapshot per interval and feeds
    every subscriber's bounded drop-oldest queue, so a slow consumer cannot
    stall production or other consumers (Sol round-1 P2 backpressure).
    """

    def __init__(self, provider: Callable[[], dict], config: MonitorApiConfig):
        if not callable(provider):
            raise MonitorApiError("MONITOR_PROVIDER_INVALID")
        if not isinstance(config, MonitorApiConfig):
            raise MonitorApiError("MONITOR_CONFIG_INVALID")
        if config.host != "127.0.0.1" and config.host != "localhost":
            raise MonitorApiError("MONITOR_HOST_MUST_BE_LOOPBACK")
        self.provider = provider
        self.config = config
        self._token = secrets.token_urlsafe(32)
        self._token_bytes = self._token.encode("utf-8")
        self._httpd: _MonitorHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._poller: threading.Thread | None = None
        self._stop = threading.Event()
        self._subscribers: list[_Subscriber] = []
        self._subscriber_lock = threading.Lock()

    @property
    def port(self) -> int | None:
        return self._httpd.server_address[1] if self._httpd is not None else None

    @property
    def token(self) -> str:
        return self._token

    @property
    def allowed_origin(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def _subscribe(self) -> _Subscriber:
        subscriber = _Subscriber(self.config.stream_queue_bound)
        with self._subscriber_lock:
            self._subscribers.append(subscriber)
        return subscriber

    def _unsubscribe(self, subscriber: _Subscriber) -> None:
        with self._subscriber_lock:
            if subscriber in self._subscribers:
                self._subscribers.remove(subscriber)

    def _offer(self, views: dict) -> None:
        """Feed every subscriber; overflow drops oldest + marks degraded."""
        with self._subscriber_lock:
            subscribers = list(self._subscribers)
        for subscriber in subscribers:
            if len(subscriber.queue) == subscriber.queue.maxlen:
                subscriber.degraded = True
            subscriber.queue.append(views)

    def _poll_loop(self) -> None:
        while not self._stop.is_set():
            try:
                views = self.provider()
            except Exception:
                views = {"error": "MONITOR_PROJECTION_UNAVAILABLE"}
            self._offer(views)
            self._stop.wait(self.config.poll_seconds)

    def start(self) -> None:
        if self._httpd is not None:
            raise MonitorApiError("MONITOR_ALREADY_RUNNING")
        self._stop.clear()
        httpd = _MonitorHTTPServer((self.config.host, self.config.port), _Handler)
        httpd.daemon_threads = True
        httpd.monitor = self  # type: ignore[attr-defined]
        self._httpd = httpd
        self._thread = threading.Thread(
            target=httpd.serve_forever, kwargs={"poll_interval": 0.05},
            daemon=True)
        self._thread.start()
        self._poller = threading.Thread(target=self._poll_loop, daemon=True)
        self._poller.start()

    def stop(self) -> None:
        self._stop.set()
        httpd, self._httpd = self._httpd, None
        thread, self._thread = self._thread, None
        poller, self._poller = self._poller, None
        if httpd is not None:
            httpd.shutdown()
            # Force-close tracked connections (including stalled/partial
            # requests) so handler threads exit promptly (Sol round-1 P1).
            httpd.close_all_connections()
            httpd.server_close()
        if thread is not None:
            thread.join(timeout=5)
        if poller is not None:
            poller.join(timeout=5)
