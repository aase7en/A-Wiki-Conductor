"""SF-WEB-1 transport tests; no installed database or browser access."""
from dataclasses import dataclass, replace
from contextlib import contextmanager
import asyncio
import json
import socket
import sqlite3
import subprocess
import sys
import threading
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from a_conductor.cockpit_projection import (
    CockpitLaneIdentity, CockpitLaneInputs, CockpitObservations,
    project_cockpit_snapshot,
)
from a_conductor.web_api import (
    WebApiConfig, WebFeed, bind_socket, create_app, public_snapshot,
    database_provider,
)
from a_conductor.monitor_api import MonitorApiError


def projection():
    return project_cockpit_snapshot(CockpitObservations(
        lanes=(CockpitLaneInputs(CockpitLaneIdentity("WO-P1-689", "task-1")),),
        generated_at="2026-10-21T00:00:00+00:00",
    ))


@pytest.fixture
def client():
    app = create_app(projection, WebApiConfig(port=18956, stream_seconds=.15))
    with TestClient(app, base_url="http://127.0.0.1:18956") as client:
        client.headers["Authorization"] = f"Bearer {app.state.feed.token}"
        yield client


def test_snapshot(client):
    response = client.get("/api/v1/snapshot")
    assert response.status_code == 200
    data = response.json()
    assert data["api_version"] == "sunday-family.monitor.v1"
    assert data["cockpit"]["lanes"][0]["state"] == "UNKNOWN"
    assert "EVIDENCE_INCOMPLETE" in data["cockpit"]["lanes"][0]["state_markers"]
    assert data["monitor"]["error"] == "MONITOR_PROJECTION_UNAVAILABLE"
    assert response.headers["cache-control"] == "no-store"
    assert client.get("/api/v1/monitor/snapshot").status_code == 200


def test_health(client):
    data = client.get("/api/v1/health").json()
    assert data["status"] == "ok"
    assert data["version"] == "0.7.0"
    assert data["profile"] == "headless-read-only"


@pytest.mark.parametrize("authorization", [None, "Bearer wrong", "Basic wrong"])
def test_auth(client, authorization):
    client.headers.pop("Authorization")
    headers = {} if authorization is None else {"Authorization": authorization}
    response = client.get("/api/v1/snapshot", headers=headers)
    assert response.status_code == 401
    assert response.json() == {"error": "MONITOR_FORBIDDEN", "gate": "TOKEN"}


@pytest.mark.parametrize("origin", ["null", "https://evil.test", "http://localhost:18956"])
def test_origin(client, origin):
    assert client.get("/api/v1/health", headers={"Origin": origin}).status_code == 403


def test_same_origin(client):
    assert client.get("/api/v1/health", headers={"Origin": "http://127.0.0.1:18956"}).status_code == 200


@pytest.mark.parametrize("host", ["localhost:18956", "evil.test:18956", "127.0.0.1:80"])
def test_rebinding(client, host):
    assert client.get("/api/v1/health", headers={"Host": host}).status_code == 403


@pytest.mark.parametrize("header", ["Host", "Origin", "Authorization"])
def test_duplicate_headers(client, header):
    response = client.get("/api/v1/health", headers=[(header, "a"), (header, "b")])
    assert response.status_code == 403
    assert response.json()["gate"].endswith("_DUPLICATE")


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
def test_read_only(client, method):
    assert client.request(method, "/api/v1/snapshot").status_code == 405
    assert all(route.methods == {"GET"} for route in client.app.routes)


def test_unknown_route(client):
    assert client.get("/private-path").json() == {"error": "MONITOR_NOT_FOUND"}


def test_sse(client):
    response = client.get("/api/v1/stream")
    assert response.headers["content-type"].startswith("text/event-stream")
    frame = response.text.split("\n\n")[0]
    event, data = frame.split("\n")
    assert event == "event: snapshot"
    assert json.loads(data.removeprefix("data: "))["cockpit"]["lanes"]
    assert not client.app.state.feed._subscribers


def test_unavailable_is_not_empty_success():
    def broken():
        raise RuntimeError("private-path-secret")
    app = create_app(broken, WebApiConfig(port=18956))
    with TestClient(app, base_url="http://127.0.0.1:18956") as client:
        client.headers["Authorization"] = f"Bearer {app.state.feed.token}"
        for path in ("health", "snapshot", "stream"):
            response = client.get(f"/api/v1/{path}")
            assert response.status_code == 503
            assert "private" not in response.text


def test_public_fields_and_stale():
    snap = projection()
    lane = replace(snap.lanes[0], identity=replace(snap.lanes[0].identity,
                   worktree="C:/private/token", provider="sk-private-secret"))
    result = public_snapshot(replace(snap, lanes=(lane,), stale=True,
                                     stale_reason="SOURCE_DRIFT_DETECTED"))
    assert result["stale"] is True
    assert "private" not in json.dumps(result)
    assert "worktree" not in result["cockpit"]["lanes"][0]["identity"]


def test_invalid_projection():
    with pytest.raises(MonitorApiError):
        public_snapshot({"lanes": []})


def test_provider_typed_error_is_not_public_payload():
    def broken():
        raise MonitorApiError("PRIVATE_SECRET")
    feed = WebFeed(broken, WebApiConfig())
    assert feed.provider() == {"error": "MONITOR_PROJECTION_UNAVAILABLE"}


def test_invalid_provider_is_rejected():
    with pytest.raises(MonitorApiError, match="MONITOR_PROVIDER_INVALID"):
        create_app(None)


def test_oversize_collection():
    with pytest.raises(MonitorApiError, match="MONITOR_FRAME_OVERSIZED"):
        public_snapshot(replace(projection(), lanes=projection().lanes * 257))


def test_unicode_byte_bound():
    from a_conductor.web_api import encode_frame
    with pytest.raises(MonitorApiError, match="MONITOR_FRAME_OVERSIZED"):
        encode_frame({"value": "\u754c" * 90_000})


def test_queue_gap_and_capacity():
    feed = WebFeed(projection, WebApiConfig(stream_queue_bound=1, max_subscribers=2))
    slow = feed.subscribe()
    fast = feed.subscribe()
    feed._offer(public_snapshot(projection()))
    assert feed.take(fast)["monitor_stream_degraded"] is False
    feed._offer(public_snapshot(projection()))
    assert feed.take(slow)["monitor_stream_degraded"] is True
    assert feed.take(fast)["monitor_stream_degraded"] is False
    with pytest.raises(MonitorApiError, match="MONITOR_CAPACITY_EXCEEDED"):
        feed.subscribe()
    feed._unsubscribe(slow)
    assert feed.subscribe() is not None


def test_capacity_returns_http_503():
    app = create_app(projection, WebApiConfig(port=18956, max_subscribers=1))
    with TestClient(app, base_url="http://127.0.0.1:18956") as client:
        client.headers["Authorization"] = f"Bearer {app.state.feed.token}"
        subscriber = app.state.feed.subscribe()
        try:
            assert client.get("/api/v1/stream").json() == {"error": "MONITOR_CAPACITY_EXCEEDED"}
        finally:
            app.state.feed._unsubscribe(subscriber)


@pytest.mark.parametrize("blocked_type", ["http.response.start", "http.response.body"])
def test_stalled_send_releases_subscription(blocked_type):
    async def exercise():
        app = create_app(projection, WebApiConfig(port=18956, send_seconds=.02))
        async with app.router.lifespan_context(app):
            scope = {"type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"},
                "http_version": "1.1", "method": "GET", "scheme": "http",
                "path": "/api/v1/stream", "query_string": b"", "root_path": "",
                "server": ("127.0.0.1", 18956), "client": ("127.0.0.1", 12345),
                "headers": [(b"host", b"127.0.0.1:18956"),
                    (b"authorization", f"Bearer {app.state.feed.token}".encode())]}

            async def receive():
                await asyncio.Event().wait()

            async def send(message):
                if message["type"] == blocked_type:
                    await asyncio.Event().wait()
            await asyncio.wait_for(app(scope, receive, send), 1)
            assert not app.state.feed._subscribers
    asyncio.run(exercise())


def test_stream_update_and_post_header_error():
    calls = []
    def changing():
        calls.append(1)
        if len(calls) > 2:
            raise RuntimeError("private-secret")
        return projection()
    app = create_app(changing, WebApiConfig(port=18956, poll_seconds=.03, stream_seconds=.2))
    with TestClient(app, base_url="http://127.0.0.1:18956") as client:
        client.headers["Authorization"] = f"Bearer {app.state.feed.token}"
        response = client.get("/api/v1/stream")
        assert "event: update\n" in response.text
        assert "event: monitor_error\n" in response.text
        assert "private" not in response.text


def test_restart_rotates_bearer():
    app = create_app(projection, WebApiConfig(port=18956))
    with TestClient(app):
        old = app.state.feed.token
    with TestClient(app, base_url="http://127.0.0.1:18956") as client:
        assert app.state.feed.token != old
        assert client.get("/api/v1/health", headers={"Authorization": f"Bearer {old}"}).status_code == 401


def test_restart_refuses_retained_subscriber():
    feed = WebFeed(projection, WebApiConfig())
    sub = feed.subscribe()
    with pytest.raises(MonitorApiError, match="MONITOR_STOP_INCOMPLETE"):
        feed.start_feed()
    feed._unsubscribe(sub)


def test_stale_cache_fails_closed():
    feed = WebFeed(projection, WebApiConfig())
    feed._offer(public_snapshot(projection()))
    feed._observed_at -= 10
    with pytest.raises(MonitorApiError, match="MONITOR_PROJECTION_UNAVAILABLE"):
        feed.current()


@pytest.mark.parametrize("host", ["0.0.0.0", "localhost", "::1", "192.168.1.1"])
def test_binding_rejects_non_numeric_loopback(host):
    with pytest.raises(MonitorApiError, match="MONITOR_HOST_MUST_BE_LOOPBACK"):
        WebApiConfig(host=host)


def test_real_socket_binding():
    with bind_socket(WebApiConfig(port=0)) as sock:
        assert sock.getsockname()[0] == "127.0.0.1"
        assert sock.getsockname()[1] > 0


def test_missing_database_never_created(tmp_path):
    path = tmp_path / "missing.sqlite"
    with pytest.raises(Exception):
        database_provider(path)()
    assert not path.exists()


def test_headless_import():
    result = subprocess.run([sys.executable, "-c", "import sys; "
        "from pathlib import Path; import a_conductor.web_api as w; "
        "w.database_provider(Path('not-opened.sqlite')); "
        "assert not any(k == 'tkinter' or k.startswith(('tkinter.', 'OpenGL', "
        "'moderngl', 'tkinterweb')) for k in sys.modules)"],
        capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr.decode()


def test_database_read_only_and_bounded(tmp_path):
    path = tmp_path / "authority.sqlite"
    with sqlite3.connect(path) as conn:
        conn.executescript("""
            CREATE TABLE execution_records (
              execution_id TEXT, job_id TEXT, work_order_ref TEXT, worker_id TEXT,
              backend_id TEXT, repo_root TEXT, branch TEXT, head_before TEXT,
              transport_state TEXT, execution_state TEXT, pid INTEGER,
              exit_code INTEGER, started_at TEXT, finished_at TEXT, created_at TEXT);
            CREATE TABLE worker_leases (
              lease_id TEXT, worker_id TEXT, worktree_key TEXT, branch TEXT,
              expected_head TEXT, acquired_at TEXT, heartbeat_at TEXT, expires_at TEXT,
              quarantined_at TEXT, quarantine_code TEXT, released_at TEXT);
        """)
        conn.execute("INSERT INTO execution_records VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("exec-1", "job-1", "WO-P1-689", "worker-1", "backend-1", str(tmp_path),
             "main", "a" * 40, "CONNECTED", "RUNNING", 123, None,
             "2026-10-21T00:00:00Z", None, "2026-10-21T00:00:00Z"))
    before = path.read_bytes()
    snapshot = database_provider(path)()
    assert snapshot.lanes[0].state.value == "RUNNING"
    assert path.read_bytes() == before
    assert set(p.name for p in tmp_path.iterdir()) == {"authority.sqlite"}
    from a_conductor.desktop_control import _read_cockpit_execution_observations
    with sqlite3.connect(path) as conn:
        conn.execute("INSERT INTO execution_records SELECT * FROM execution_records")
    with pytest.raises(ValueError, match="MONITOR_FRAME_OVERSIZED"):
        _read_cockpit_execution_observations(path, row_limit=1)
    assert len(_read_cockpit_execution_observations(path)) == 2


def test_reject_before_request_provider_invocation():
    calls = []
    app = create_app(lambda: calls.append(1) or projection(), WebApiConfig(port=18956))
    with TestClient(app, base_url="http://127.0.0.1:18956") as client:
        before = len(calls)
        assert client.get("/api/v1/snapshot").status_code == 401
        assert len(calls) == before


def test_real_uvicorn_sse_disconnect():
    import uvicorn
    config = WebApiConfig(port=0, poll_seconds=.02)
    with bind_socket(config) as sock:
        port = sock.getsockname()[1]
        app = create_app(projection, replace(config, port=port))
        server = uvicorn.Server(uvicorn.Config(app, log_level="critical", access_log=False,
            proxy_headers=False, timeout_graceful_shutdown=1))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 5
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(.01)
            assert server.started
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=2,
                              trust_env=False) as client:
                client.headers["Authorization"] = f"Bearer {app.state.feed.token}"
                for _ in range(2):
                    with client.stream("GET", "/api/v1/stream") as response:
                        lines = response.iter_lines()
                        assert next(lines) == "event: snapshot"
                        assert next(lines).startswith("data: ")
                    deadline = time.monotonic() + 2
                    while app.state.feed._subscribers and time.monotonic() < deadline:
                        time.sleep(.01)
                    assert not app.state.feed._subscribers
        finally:
            server.should_exit = True
            thread.join(5)
        assert not thread.is_alive()
        assert app.state.feed._poller is None


@contextmanager
def running_web_cli(monkeypatch, config):
    import uvicorn
    from a_conductor import web_api

    servers = []
    server_class = uvicorn.Server

    @dataclass(frozen=True)
    class CliConfig(WebApiConfig):
        max_connections: int = config.max_connections
        header_seconds: float = config.header_seconds

    def capture(uvicorn_config):
        server = server_class(uvicorn_config)
        servers.append(server)
        return server

    with monkeypatch.context() as patch:
        patch.setattr(web_api, "WebApiConfig", CliConfig)
        patch.setattr(web_api, "database_provider", lambda path: projection)
        patch.setattr(uvicorn, "Server", capture)
        thread = threading.Thread(target=web_api.main,
            args=(["web", "--database", "unused.sqlite", "--port", "0"],), daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 5
            while (not servers or not servers[0].started) and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(.01)
            assert servers and servers[0].started
            yield servers[0]
        finally:
            if servers:
                servers[0].should_exit = True
            thread.join(5)
        assert not thread.is_alive()
        assert not servers[0].server_state.connections
        assert servers[0].config.app.state.feed._poller is None


@pytest.mark.parametrize("prefix", [b"", b"GET /api/v1/health HTTP/1.1\r\nHost:"])
def test_initial_headers_bounded_and_expire(monkeypatch, prefix):
    config = WebApiConfig(port=0)
    with running_web_cli(monkeypatch, config) as server:
        port = server.config.port
        sockets = []
        try:
            for _ in range(40):
                peer = socket.create_connection(("127.0.0.1", port), timeout=2)
                sockets.append(peer)
                if prefix:
                    peer.sendall(prefix)
            time.sleep(.1)
            admitted = len(server.server_state.connections)
            deadline = time.monotonic() + 5.5
            while server.server_state.connections and time.monotonic() < deadline:
                time.sleep(.01)
            remaining = len(server.server_state.connections)
            with httpx.Client(trust_env=False, timeout=2) as client:
                response = client.get(f"http://127.0.0.1:{port}/api/v1/health",
                    headers={"Authorization": f"Bearer {server.config.app.state.feed.token}"})
            assert response.status_code == 200, (response.status_code, admitted, remaining)
            assert admitted <= config.max_connections
            assert remaining == 0
            for peer in sockets:
                try:
                    assert peer.recv(1) == b""
                except (ConnectionResetError, ConnectionAbortedError):
                    pass
        finally:
            for peer in sockets:
                peer.close()


def test_header_deadline_not_extended_by_trickle_or_keepalive(monkeypatch):
    config = WebApiConfig(port=0, header_seconds=.3)
    with running_web_cli(monkeypatch, config) as server:
        port = server.config.port
        for reused in (False, True):
            with socket.create_connection(("127.0.0.1", port), timeout=2) as peer:
                if reused:
                    peer.sendall((f"GET /api/v1/health HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
                        f"Authorization: Bearer {server.config.app.state.feed.token}\r\n\r\n").encode())
                    response = b""
                    while b"\r\n\r\n" not in response:
                        response += peer.recv(4096)
                    assert response.startswith(b"HTTP/1.1 200")
                    headers, body = response.split(b"\r\n\r\n", 1)
                    length = int(next(line.split(b":", 1)[1] for line in headers.split(b"\r\n")
                        if line.lower().startswith(b"content-length:")))
                    while len(body) < length:
                        body += peer.recv(4096)
                peer.sendall(b"GET /api/v1/health HTTP/1.1\r\nHost:")
                started = time.monotonic()
                while time.monotonic() - started < .6:
                    try:
                        peer.sendall(b" ")
                    except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                        break
                    time.sleep(.04)
                try:
                    assert peer.recv(1) == b""
                except (ConnectionResetError, ConnectionAbortedError):
                    pass
                assert time.monotonic() - started < 1


def test_transport_capacity_boundary_and_restart_cleanup(monkeypatch):
    config = WebApiConfig(port=0, max_connections=2, header_seconds=.5)
    for _ in range(2):
        with running_web_cli(monkeypatch, config) as server:
            port = server.config.port
            assert server.config.limit_concurrency == 2
            with socket.create_connection(("127.0.0.1", port), timeout=2) as idle:
                with httpx.Client(trust_env=False, timeout=2) as client:
                    response = client.get(f"http://127.0.0.1:{port}/api/v1/health",
                        headers={"Authorization": f"Bearer {server.config.app.state.feed.token}"})
                    assert response.status_code == 200
                    time.sleep(.02)
                    assert len(server.server_state.connections) == 2
                    with socket.create_connection(("127.0.0.1", port), timeout=2) as excess:
                        try:
                            assert excess.recv(1) == b""
                        except (ConnectionResetError, ConnectionAbortedError):
                            pass
                    assert len(server.server_state.connections) <= 2
                # Leave an incomplete connection open until server shutdown.
            deadline = time.monotonic() + 1
            while server.server_state.connections and time.monotonic() < deadline:
                time.sleep(.01)
            assert not server.server_state.connections
            pending = socket.create_connection(("127.0.0.1", port), timeout=2)
            try:
                time.sleep(.02)
                protocols = tuple(server.server_state.connections)
                assert protocols
                assert any(protocol._header_timer is not None for protocol in protocols)
            finally:
                server.should_exit = True
        try:
            assert all(protocol._header_timer is None for protocol in protocols)
            assert pending.recv(1) == b""
        finally:
            pending.close()


def test_complete_headers_cancel_deadline_for_live_stream(monkeypatch):
    config = WebApiConfig(port=0, header_seconds=.1)
    with running_web_cli(monkeypatch, config) as server:
        with httpx.Client(trust_env=False, timeout=2) as client:
            with client.stream("GET", f"http://127.0.0.1:{server.config.port}/api/v1/stream",
                    headers={"Authorization": f"Bearer {server.config.app.state.feed.token}"}) as response:
                assert response.status_code == 200
                lines = response.iter_lines()
                assert next(lines) == "event: snapshot"
                assert next(lines).startswith("data: ")
                time.sleep(.25)
                protocols = tuple(server.server_state.connections)
                assert len(protocols) == 1
                assert protocols[0]._header_timer is None
                assert not protocols[0].transport.is_closing()


@pytest.mark.parametrize("seconds", [0, -1, 5.1, float("inf"), float("nan"), True])
def test_invalid_header_deadline(seconds):
    with pytest.raises(MonitorApiError, match="MONITOR_CONFIG_INVALID"):
        WebApiConfig(header_seconds=seconds)
