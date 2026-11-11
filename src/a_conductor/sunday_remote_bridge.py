"""Self-hosted, local-first transport adapter for SunDay Runtime.

The bridge authenticates every request with ``sunday_remote_protocol`` and
exposes only typed runtime operations.  It deliberately has no raw-shell,
scheduler, task, claim, provider, review, retry, completion, merge, or project
memory authority.

The built-in HTTP server defaults to loopback.  Remote access is expected to be
provided by a separately-authorized encrypted tunnel/reverse proxy that forwards
to this loopback listener.  Non-loopback bind addresses fail closed by default.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ipaddress import ip_address
from pathlib import Path
from threading import Lock
from typing import Callable, Mapping, Sequence

from .native_execution import NativeExecutionError
from .sunday_remote_protocol import (
    DEFAULT_MAX_BODY_BYTES,
    RemoteProtocolError,
    ReplayWindow,
    parse_and_verify_request,
)
from .sunday_runtime import SunDayRuntime, SunDayRuntimeError


class SunDayRemoteBridgeError(RuntimeError):
    """Stable transport/dispatch failure classification."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _text(value: object, code: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise SunDayRemoteBridgeError(code)
    return value.strip()


def _optional_text(value: object, code: str) -> str | None:
    if value is None:
        return None
    return _text(value, code)


def _positive_int(value: object, code: str, *, default: int | None = None) -> int:
    if value is None and default is not None:
        return default
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise SunDayRemoteBridgeError(code)
    return value


def _string_sequence(value: object, code: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise SunDayRemoteBridgeError(code)
    rendered: list[str] = []
    for item in value:
        rendered.append(_text(item, code))
    if not rendered and not allow_empty:
        raise SunDayRemoteBridgeError(code)
    return tuple(rendered)


def _jsonable(value: object) -> object:
    if is_dataclass(value):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _json_bytes(payload: Mapping[str, object]) -> bytes:
    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise SunDayRemoteBridgeError("RESPONSE_ENCODING_FAILED") from exc


@dataclass(frozen=True, slots=True)
class RemoteBridgeResponse:
    status_code: int
    body: bytes


class SunDayRemoteBridge:
    """Authenticated typed-operation facade over one bound ``SunDayRuntime``."""

    def __init__(
        self,
        runtime: SunDayRuntime,
        *,
        shared_secret: bytes,
        replay_window: ReplayWindow | None = None,
        clock_ms: Callable[[], int] | None = None,
        max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
    ) -> None:
        if not isinstance(runtime, SunDayRuntime):
            raise ValueError("runtime must be a SunDayRuntime")
        if not isinstance(shared_secret, (bytes, bytearray, memoryview)):
            raise ValueError("shared_secret must be bytes-like and at least 32 bytes")
        secret_bytes = bytes(shared_secret)
        if len(secret_bytes) < 32:
            raise ValueError("shared_secret must be bytes-like and at least 32 bytes")
        if not isinstance(max_body_bytes, int) or isinstance(max_body_bytes, bool) or max_body_bytes < 1:
            raise ValueError("max_body_bytes must be a positive integer")
        self._runtime = runtime
        self._shared_secret = secret_bytes
        self._replay_window = replay_window or ReplayWindow()
        self._clock_ms = clock_ms
        self._max_body_bytes = max_body_bytes
        self._mutation_lock = Lock()

    @property
    def runtime(self) -> SunDayRuntime:
        return self._runtime

    @property
    def max_body_bytes(self) -> int:
        return self._max_body_bytes

    def _dispatch(self, operation: str, payload: Mapping[str, object]) -> object:
        if operation == "context.verify":
            if payload:
                raise SunDayRemoteBridgeError("PAYLOAD_INVALID")
            return self._runtime.verify_context()

        if operation == "fs.read":
            path = _text(payload.get("path"), "PAYLOAD_INVALID")
            max_bytes_raw = payload.get("max_bytes")
            max_bytes = None if max_bytes_raw is None else _positive_int(max_bytes_raw, "PAYLOAD_INVALID")
            return self._runtime.read_text(path, max_bytes=max_bytes)

        if operation == "fs.list":
            path = payload.get("path", ".")
            return self._runtime.list_directory(_text(path, "PAYLOAD_INVALID"))

        if operation == "fs.create":
            path = _text(payload.get("path"), "PAYLOAD_INVALID")
            content = payload.get("content")
            if not isinstance(content, str):
                raise SunDayRemoteBridgeError("PAYLOAD_INVALID")
            with self._mutation_lock:
                return self._runtime.create_text_if_absent(path, content)

        if operation == "fs.write":
            path = _text(payload.get("path"), "PAYLOAD_INVALID")
            content = payload.get("content")
            if not isinstance(content, str):
                raise SunDayRemoteBridgeError("PAYLOAD_INVALID")
            expected_sha256 = _optional_text(payload.get("expected_sha256"), "PAYLOAD_INVALID")
            with self._mutation_lock:
                return self._runtime.write_text(
                    path,
                    content,
                    expected_sha256=expected_sha256,
                )

        if operation == "search.text":
            query = _text(payload.get("query"), "PAYLOAD_INVALID")
            raw_paths = payload.get("paths", ["."])
            paths = _string_sequence(raw_paths, "PAYLOAD_INVALID")
            timeout_seconds = _positive_int(
                payload.get("timeout_seconds"),
                "PAYLOAD_INVALID",
                default=30,
            )
            return self._runtime.search_text(
                query,
                paths,
                timeout_seconds=timeout_seconds,
            )

        if operation == "command.run":
            argv = _string_sequence(payload.get("argv"), "PAYLOAD_INVALID")
            cwd = _text(payload.get("cwd", "."), "PAYLOAD_INVALID")
            timeout_seconds = _positive_int(
                payload.get("timeout_seconds"),
                "PAYLOAD_INVALID",
                default=30,
            )
            mutation_intent = payload.get("mutation_intent", False)
            if not isinstance(mutation_intent, bool):
                raise SunDayRemoteBridgeError("PAYLOAD_INVALID")
            if mutation_intent:
                with self._mutation_lock:
                    return self._runtime.run_allowlisted(
                        argv,
                        cwd=cwd,
                        timeout_seconds=timeout_seconds,
                        mutation_intent=True,
                    )
            return self._runtime.run_allowlisted(
                argv,
                cwd=cwd,
                timeout_seconds=timeout_seconds,
                mutation_intent=False,
            )

        raise SunDayRemoteBridgeError("OPERATION_NOT_ALLOWED")

    def handle(self, body: bytes) -> RemoteBridgeResponse:
        """Authenticate, replay-check, dispatch and serialize one request."""

        try:
            request = parse_and_verify_request(
                body,
                secret=self._shared_secret,
                replay_window=self._replay_window,
                clock_ms=self._clock_ms,
                max_body_bytes=self._max_body_bytes,
            )
            result = self._dispatch(request.operation, request.payload)
            response = {
                "ok": True,
                "request_id": request.request_id,
                "result": _jsonable(result),
            }
            return RemoteBridgeResponse(HTTPStatus.OK, _json_bytes(response))
        except RemoteProtocolError as exc:
            status = HTTPStatus.UNAUTHORIZED if exc.code == "AUTH_INVALID" else HTTPStatus.BAD_REQUEST
            if exc.code == "REPLAY_DETECTED":
                status = HTTPStatus.CONFLICT
            return RemoteBridgeResponse(
                status,
                _json_bytes({"ok": False, "error": exc.code}),
            )
        except SunDayRemoteBridgeError as exc:
            status = HTTPStatus.FORBIDDEN if exc.code == "OPERATION_NOT_ALLOWED" else HTTPStatus.BAD_REQUEST
            return RemoteBridgeResponse(
                status,
                _json_bytes({"ok": False, "error": exc.code}),
            )
        except (SunDayRuntimeError, NativeExecutionError) as exc:
            code = getattr(exc, "code", None) or (exc.args[0] if exc.args else "RUNTIME_FAILED")
            return RemoteBridgeResponse(
                HTTPStatus.CONFLICT,
                _json_bytes({"ok": False, "error": str(code)}),
            )


def _is_loopback_host(host: str) -> bool:
    normalized = host.strip().lower()
    if normalized in {"localhost", "localhost."}:
        return True
    try:
        return ip_address(normalized).is_loopback
    except ValueError:
        return False


def build_http_server(
    bridge: SunDayRemoteBridge,
    *,
    host: str = "127.0.0.1",
    port: int = 0,
    allow_insecure_non_loopback: bool = False,
) -> ThreadingHTTPServer:
    """Build a stdlib HTTP server; caller owns ``serve_forever``/shutdown.

    The default loopback-only bind is safe to place behind a separately-managed
    encrypted tunnel.  Direct non-loopback HTTP is blocked unless the caller
    explicitly opts in; HMAC authenticates requests but does not encrypt them.
    """

    if not isinstance(bridge, SunDayRemoteBridge):
        raise ValueError("bridge must be a SunDayRemoteBridge")
    host_text = _text(host, "BIND_ADDRESS_INVALID")
    if not _is_loopback_host(host_text) and not allow_insecure_non_loopback:
        raise SunDayRemoteBridgeError("NON_LOOPBACK_BIND_REQUIRES_EXPLICIT_OPT_IN")
    if not isinstance(port, int) or isinstance(port, bool) or not 0 <= port <= 65_535:
        raise SunDayRemoteBridgeError("PORT_INVALID")

    class Handler(BaseHTTPRequestHandler):
        server_version = "SunDayRuntimeBridge/1"
        sys_version = ""

        def log_message(self, format: str, *args: object) -> None:  # noqa: A003
            return

        def _write(self, status: int, body: bytes) -> None:
            self.send_response(int(status))
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            if self.path != "/healthz":
                self._write(HTTPStatus.NOT_FOUND, _json_bytes({"ok": False, "error": "NOT_FOUND"}))
                return
            evidence = bridge.runtime.verify_context()
            digest = hashlib.sha256(
                f"{evidence.worktree_root}|{evidence.branch}|{evidence.head}|{evidence.claim_id}".encode("utf-8")
            ).hexdigest()
            self._write(
                HTTPStatus.OK,
                _json_bytes({"ok": True, "context_sha256": digest}),
            )

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/v1/call":
                self._write(HTTPStatus.NOT_FOUND, _json_bytes({"ok": False, "error": "NOT_FOUND"}))
                return
            content_length = self.headers.get("Content-Length")
            if content_length is None:
                self._write(HTTPStatus.LENGTH_REQUIRED, _json_bytes({"ok": False, "error": "CONTENT_LENGTH_REQUIRED"}))
                return
            try:
                length = int(content_length)
            except ValueError:
                self._write(HTTPStatus.BAD_REQUEST, _json_bytes({"ok": False, "error": "CONTENT_LENGTH_INVALID"}))
                return
            if length < 0 or length > bridge.max_body_bytes:
                self._write(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, _json_bytes({"ok": False, "error": "REQUEST_TOO_LARGE"}))
                return
            result = bridge.handle(self.rfile.read(length))
            self._write(result.status_code, result.body)

    return ThreadingHTTPServer((host_text, port), Handler)
