"""SF-WEB-1: headless read-only ASGI view over existing cockpit authorities.

No import-time listener, GUI, store creation or command authority. The legacy
monitor owns producer/queue/lifecycle mechanics; this adapter adds a bounded
public serializer, SSE framing and an independently authenticated ASGI surface.
"""
from __future__ import annotations

import argparse
import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, replace
from datetime import datetime
import json
from pathlib import Path
import re
import secrets
import socket
import threading
import time

from fastapi import FastAPI
import h11
from starlette.requests import ClientDisconnect
from starlette.responses import JSONResponse, Response, StreamingResponse
from uvicorn.protocols.http.h11_impl import H11Protocol

from .branding import APP_VERSION
from .cockpit_projection import CockpitSnapshot
from .monitor_api import MonitorApiConfig, MonitorApiError, MonitorApiServer
from .web_api_auth import WebApiAuth

API_VERSION = "sunday-family.monitor.v1"
MAX_FRAME_BYTES = 262_144
_CODE = re.compile(r"[A-Z][A-Z0-9_:\-]{0,127}\Z")
_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:#\-]{0,127}\Z")


@dataclass(frozen=True)
class WebApiConfig(MonitorApiConfig):
    port: int = 8756
    max_subscribers: int = 16
    max_connections: int = 32
    stream_seconds: float = 300
    request_seconds: float = 10
    send_seconds: float = 10
    header_seconds: float = 5

    def __post_init__(self):
        super().__post_init__()
        if self.host != "127.0.0.1":
            raise MonitorApiError("MONITOR_HOST_MUST_BE_LOOPBACK")
        for value, maximum in ((self.max_subscribers, 64), (self.max_connections, 128)):
            if type(value) is not int or not 1 <= value <= maximum:
                raise MonitorApiError("MONITOR_CONFIG_INVALID")
        for value, maximum in ((self.stream_seconds, 300), (self.request_seconds, 30),
                               (self.send_seconds, 30), (self.header_seconds, 5)):
            if type(value) not in (int, float) or not 0 < value <= maximum:
                raise MonitorApiError("MONITOR_CONFIG_INVALID")


def encode_frame(value: dict) -> bytes:
    body = json.dumps(value, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")
    if len(body) > MAX_FRAME_BYTES:
        raise MonitorApiError("MONITOR_FRAME_OVERSIZED")
    return body


def _text(value, *, code=False):
    if value is None:
        return None
    pattern = _CODE if code else _REF
    if (not isinstance(value, str) or not pattern.fullmatch(value)
            or value.lower().startswith(("sk-", "bearer", "token", "password", "secret"))):
        raise MonitorApiError("MONITOR_PROJECTION_UNAVAILABLE")
    return value


def _stamp(value):
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > 40:
        raise MonitorApiError("MONITOR_PROJECTION_UNAVAILABLE")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise MonitorApiError("MONITOR_PROJECTION_UNAVAILABLE")
    return value


def public_snapshot(snapshot: CockpitSnapshot) -> dict:
    """Explicit DTO: no paths, logs, arbitrary prose, provider config or asdict."""
    if not isinstance(snapshot, CockpitSnapshot):
        raise MonitorApiError("MONITOR_PROJECTION_UNAVAILABLE")
    if len(snapshot.lanes) > 256 or len(snapshot.degraded_observability) > 256:
        raise MonitorApiError("MONITOR_FRAME_OVERSIZED")
    lanes = []
    for lane in snapshot.lanes:
        if len(lane.state_markers) > 16:
            raise MonitorApiError("MONITOR_FRAME_OVERSIZED")
        identity = {field: _text(getattr(lane.identity, field)) for field in (
            "work_order_ref", "task_ref", "lane", "execution_id", "lease_id",
            "provenance",
        )}
        view = {"identity": identity, "state": lane.state.value,
                "state_markers": [_text(v, code=True) for v in lane.state_markers]}
        for field in ("blocker_code", "transport_state", "capacity_class", "wait_reason",
                      "replay_safety", "next_safe_action", "hook_state", "wtl_state"):
            view[field] = _text(getattr(lane, field), code=True)
        for field in ("execution_id", "job_id"):
            view[field] = _text(getattr(lane, field))
        for field in ("last_activity", "last_meaningful_progress", "next_recheck_at"):
            view[field] = _stamp(getattr(lane, field))
        if lane.countdown_seconds is not None and (
            type(lane.countdown_seconds) is not int or not 0 <= lane.countdown_seconds <= 2**31
        ):
            raise MonitorApiError("MONITOR_PROJECTION_UNAVAILABLE")
        if lane.active_mutation_child is not None and type(lane.active_mutation_child) is not bool:
            raise MonitorApiError("MONITOR_PROJECTION_UNAVAILABLE")
        view["countdown_seconds"] = lane.countdown_seconds
        view["active_mutation_child"] = lane.active_mutation_child
        view["gates"] = {name: getattr(lane.gates, name).value for name in (
            "verification", "review", "merge", "post_main", "ci",
        )}
        view["gates"]["provenance"] = _text(lane.gates.provenance, code=True)
        view["origin_display"] = {
            "status": _text(lane.origin_display.status, code=True),
            "reason": _text(lane.origin_display.reason, code=True),
            "origin_ref": _text(lane.origin_display.origin_ref),
            "origin_surface": _text(lane.origin_display.origin_surface),
        }
        lanes.append(view)
    if type(snapshot.stale) is not bool:
        raise MonitorApiError("MONITOR_PROJECTION_UNAVAILABLE")
    result = {
        "api_version": API_VERSION, "generated_at": _stamp(snapshot.generated_at),
        "cockpit": {"lanes": lanes},
        "monitor": {"error": "MONITOR_PROJECTION_UNAVAILABLE", "gate": "OPTIONAL_READ_PORT_UNAVAILABLE"},
        "stale": snapshot.stale, "stale_reason": _text(snapshot.stale_reason, code=True),
        "degraded_observability": [_text(v) for v in snapshot.degraded_observability],
        "monitor_stream_degraded": False,
    }
    encode_frame(result)
    return result


class WebFeed(MonitorApiServer):
    """Reuse legacy bounded queues/poller; never start its HTTP listener."""

    def __init__(self, provider, config):
        if not callable(provider):
            raise MonitorApiError("MONITOR_PROVIDER_INVALID")
        if not isinstance(config, WebApiConfig):
            raise MonitorApiError("MONITOR_CONFIG_INVALID")

        def read():
            try:
                source = provider()
            except Exception:
                return {"error": "MONITOR_PROJECTION_UNAVAILABLE"}
            try:
                return public_snapshot(source)
            except MonitorApiError as exc:
                return {"error": exc.code}
            except Exception:
                return {"error": "MONITOR_PROJECTION_UNAVAILABLE"}
        super().__init__(read, config)
        self._view_lock = threading.RLock()
        self._latest = None
        self._observed_at = 0.0

    def _offer(self, views):
        with self._view_lock:
            self._latest, self._observed_at = views, time.monotonic()
            super()._offer(views)

    def current(self):
        with self._view_lock:
            if self._latest is None or time.monotonic() - self._observed_at > max(2, self.config.poll_seconds * 3):
                raise MonitorApiError("MONITOR_PROJECTION_UNAVAILABLE")
            if "error" in self._latest:
                raise MonitorApiError(self._latest["error"])
            return dict(self._latest)

    def subscribe(self):
        with self._view_lock:
            if len(self._subscribers) >= self.config.max_subscribers:
                raise MonitorApiError("MONITOR_CAPACITY_EXCEEDED")
            return self._subscribe()

    def take(self, subscriber):
        with self._view_lock:
            if not subscriber.queue:
                return None
            view = dict(subscriber.queue.popleft())
            if "error" not in view:
                view["monitor_stream_degraded"] = subscriber.degraded
            subscriber.degraded = False
            return view

    def start_feed(self):
        if self._poller is not None:
            raise MonitorApiError("MONITOR_POLLER_TERMINATING")
        if self._subscribers:
            raise MonitorApiError("MONITOR_STOP_INCOMPLETE")
        self._token = secrets.token_urlsafe(32)
        self._token_bytes = self._token.encode("ascii")
        self._latest = None
        self._generation += 1
        self._stop = threading.Event()
        self._poller = threading.Thread(target=self._poll_loop,
            args=(self._stop, self._generation), daemon=True, name="sf-web-monitor")
        self._poller.start()


class _SubscriberResponse(StreamingResponse):
    def __init__(self, content, *, feed, subscriber):
        super().__init__(content, media_type="text/event-stream",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
        self.feed, self.subscriber = feed, subscriber

    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        except ClientDisconnect:
            pass
        finally:
            # Also covers disconnect/timeout before the generator's first iteration.
            await self.body_iterator.aclose()
            self.feed._unsubscribe(self.subscriber)


def create_app(provider, config: WebApiConfig | None = None) -> FastAPI:
    config = config or WebApiConfig()
    feed = WebFeed(provider, config)

    @asynccontextmanager
    async def lifespan(app):
        feed.start_feed()
        try:
            deadline = time.monotonic() + config.request_seconds
            while feed._latest is None and time.monotonic() < deadline:
                await asyncio.sleep(.01)
            yield
        finally:
            await asyncio.to_thread(feed.stop)

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.feed = feed
    app.add_middleware(WebApiAuth, feed=feed, config=config)

    @app.exception_handler(MonitorApiError)
    async def failure(request, exc):
        return JSONResponse({"error": exc.code}, status_code=503,
                            headers={"Cache-Control": "no-store"})

    @app.exception_handler(404)
    async def missing(request, exc):
        return JSONResponse({"error": "MONITOR_NOT_FOUND"}, status_code=404,
                            headers={"Cache-Control": "no-store"})

    @app.get("/api/v1/health")
    async def health():
        view = feed.current()
        conditions = view["degraded_observability"]
        return JSONResponse({"status": "ok", "api_version": API_VERSION,
                             "version": APP_VERSION, "profile": "headless-read-only",
                             "conditions": conditions + ["OPTIONAL_MONITOR_UNAVAILABLE"],
                             "degraded": True},
                            headers={"Cache-Control": "no-store"})

    @app.get("/api/v1/snapshot")
    @app.get("/api/v1/monitor/snapshot")
    async def snapshot():
        return Response(encode_frame(feed.current()), media_type="application/json",
                        headers={"Cache-Control": "no-store"})

    @app.get("/api/v1/stream")
    @app.get("/api/v1/events")
    async def stream():
        initial = feed.current()
        subscriber = feed.subscribe()
        generation, stop_event = feed._generation, feed._stop

        async def events():
            try:
                yield b"event: snapshot\ndata: " + encode_frame(initial) + b"\n\n"
                deadline = time.monotonic() + config.stream_seconds
                heartbeat = time.monotonic() + 15
                while (time.monotonic() < deadline and not stop_event.is_set()
                       and generation == feed._generation):
                    frame = feed.take(subscriber)
                    if frame is not None:
                        kind = b"monitor_error" if "error" in frame else b"update"
                        try:
                            body = encode_frame(frame)
                        except MonitorApiError:
                            kind, body = b"monitor_error", b'{"error":"MONITOR_FRAME_OVERSIZED"}'
                        yield b"event: " + kind + b"\ndata: " + body + b"\n\n"
                    else:
                        try:
                            feed.current()
                        except MonitorApiError:
                            yield b'event: monitor_error\ndata: {"error":"MONITOR_PROJECTION_UNAVAILABLE"}\n\n'
                            break
                        if time.monotonic() >= heartbeat:
                            yield b": heartbeat\n\n"
                            heartbeat = time.monotonic() + 15
                    await asyncio.sleep(.01)
            finally:
                feed._unsubscribe(subscriber)
        return _SubscriberResponse(events(), feed=feed, subscriber=subscriber)

    return app


def database_provider(database: Path):
    """Bind an operator path once; reuse existing read ports, never initialize DBs."""
    from .desktop_control import (
        _read_cockpit_execution_observations, _read_cockpit_lease_observations,
    )
    from .control_center import ControlCenterSnapshot
    from .cockpit_projection import (
        CockpitObservations, build_observed_lane_inputs, project_cockpit_snapshot,
    )
    from datetime import timezone

    database = database.expanduser().resolve()

    def read():
        now = datetime.now(timezone.utc)

        def pin():
            executions = _read_cockpit_execution_observations(database, row_limit=256)
            leases = _read_cockpit_lease_observations(database, now, row_limit=256)
            lanes = build_observed_lane_inputs(ControlCenterSnapshot((), ()), executions,
                leases, execution_authority_readable=True, lease_authority_readable=True)
            return CockpitObservations(lanes=lanes, generated_at=now.isoformat())

        result = project_cockpit_snapshot(pin(), recheck=pin())
        return replace(result, degraded_observability=result.degraded_observability + (
            "CONTROL_CENTER_READ_PORT_UNAVAILABLE", "ACTIVITY_READER_UNAVAILABLE"))
    return read


def bind_socket(config: WebApiConfig):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        sock.bind((config.host, config.port))
        sock.listen(config.max_connections)
        return sock
    except BaseException:
        sock.close()
        raise


class _BoundedH11Protocol(H11Protocol):
    """Bound sockets and header parsing before an ASGI scope can exist."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._bounds = self.config.app.state.feed.config
        self._header_timer = None
        self._admitted = False
        # Upstream uses >= and counts this socket too; admission below already
        # enforces the inclusive socket cap. Retain its task-limit fallback.
        self.limit_concurrency = self._bounds.max_connections + 1

    def connection_made(self, transport):
        if len(self.connections) >= self._bounds.max_connections:
            self.transport = transport
            transport.abort()
            return
        super().connection_made(transport)
        self._admitted = True
        self._arm_header_deadline()

    def _cancel_header_deadline(self):
        if self._header_timer is not None:
            self._header_timer.cancel()
            self._header_timer = None

    def _arm_header_deadline(self):
        self._cancel_header_deadline()
        self._header_timer = self.loop.call_later(
            self._bounds.header_seconds, self.transport.abort)

    def data_received(self, data):
        if self._admitted and not self.transport.is_closing():
            super().data_received(data)

    def handle_events(self):
        super().handle_events()
        if self.conn.their_state is not h11.IDLE:
            self._cancel_header_deadline()

    def on_response_complete(self):
        # Also cover partial headers on reused connections: upstream cancels its
        # keep-alive timer on the first byte, not when headers finish parsing.
        self._arm_header_deadline()
        super().on_response_complete()

    def connection_lost(self, exc):
        self._cancel_header_deadline()
        super().connection_lost(exc)

    def shutdown(self):
        self._cancel_header_deadline()
        super().shutdown()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only loopback Monitor API")
    parser.add_argument("command", choices=("web",))
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8756)
    args = parser.parse_args(argv)
    import uvicorn

    config = WebApiConfig(port=args.port)
    with bind_socket(config) as sock:
        config = replace(config, port=sock.getsockname()[1])
        app = create_app(database_provider(args.database), config)
        # Token retrieval is deliberately in-process only; no stdout, URL or file handoff.
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=config.port,
            http=_BoundedH11Protocol, ws="none",
            workers=1, reload=False, access_log=False, log_level="critical",
            proxy_headers=False, server_header=False, limit_concurrency=config.max_connections,
            timeout_keep_alive=5, timeout_graceful_shutdown=10))
        server.run(sockets=[sock])


if __name__ == "__main__":
    main()
