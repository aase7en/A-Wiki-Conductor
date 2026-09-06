"""WO-P1-158 Phase C — ZCode app-server protocol driver (no process lifecycle).

The protocol driver speaks bounded JSON-lines over an ALREADY STARTED child
supplied through an injected transport. It cannot spawn, start, stop,
terminate, or kill any process: no subprocess/os/psutil imports exist here and
no lifecycle method exists on its surface. Process lifecycle belongs to the
supervised helper (Phase D) built on the shared SupervisedRunCoordinator.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Protocol


ZCODE_MAX_RESPONSE_BYTES = 64 * 1024
_PROTOCOL_ERROR_RE = re.compile(r"(?i)(api[_ -]?key|token|authorization|cookie|secret)")
_MAX_REASON = 128


class ZCodeProtocolError(RuntimeError):
    """Bounded, typed protocol failure; never carries secret material."""

    def __init__(self, code: str, detail: str | None = None) -> None:
        if not isinstance(code, str) or not re.fullmatch(r"[A-Z0-9_]{3,64}", code):
            raise ValueError("protocol error code is invalid")
        safe_detail = None
        if detail is not None:
            text = detail[:_MAX_REASON]
            if _PROTOCOL_ERROR_RE.search(text):
                text = "[REDACTED]"
            safe_detail = text
        self.code = code
        self.detail = safe_detail
        super().__init__(code)


class ZCodeProtocolTransport(Protocol):
    def send_line(self, text: str) -> None: ...
    def read_line(self, timeout_seconds: float) -> str | None: ...
    def alive(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class ZCodeProtocolTurn:
    response_text: str
    session_id: str | None
    turn_completed: bool
    bytes_received: int


class ZCodeProtocolDriver:
    """Drive ONE bounded prompt turn over a started app-server transport.

    Wire shape (observed 0.16.5, evidence only): session/create ->
    requestRuntimePreferences reply (nativeSearchEnhancementsEnabled=false) ->
    session/subscribe -> optional session/setThoughtLevel -> session/send ->
    session/event model.streaming text deltas -> turn.completed/turn.failed.
    """

    def __init__(
        self,
        transport: ZCodeProtocolTransport,
        *,
        read_timeout_seconds: float = 1.0,
        max_response_bytes: int = ZCODE_MAX_RESPONSE_BYTES,
    ) -> None:
        for method in ("send_line", "read_line", "alive"):
            if not callable(getattr(transport, method, None)):
                raise ValueError(f"transport must provide {method}")
        if (
            isinstance(read_timeout_seconds, (int, float)) is False
            or read_timeout_seconds <= 0
        ):
            raise ValueError("read_timeout_seconds must be positive")
        if (
            isinstance(max_response_bytes, bool)
            or not isinstance(max_response_bytes, int)
            or max_response_bytes < 1
            or max_response_bytes > ZCODE_MAX_RESPONSE_BYTES
        ):
            raise ValueError("max_response_bytes exceeds the production cap")
        self._transport = transport
        self._read_timeout = float(read_timeout_seconds)
        self._max_response_bytes = max_response_bytes

    def _send(self, message: dict) -> None:
        self._transport.send_line(json.dumps(message, separators=(",", ":")))

    def run_turn(
        self,
        prompt: str,
        *,
        workspace: str,
        mode: str = "plan",
        thought_level: str | None = None,
        deadline_seconds: float = 300.0,
    ) -> ZCodeProtocolTurn:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must not be blank")
        if mode not in {"plan", "build"}:
            raise ValueError("mode is invalid")
        if thought_level not in (None, "min", "low", "medium", "high", "max"):
            raise ValueError("thought_level is invalid")
        if deadline_seconds <= 0:
            raise ValueError("deadline is invalid")

        session_id: str | None = None
        deltas: list[str] = []
        received = 0
        subscribed = False
        prompt_sent = False

        import time as _time

        deadline = _time.monotonic() + deadline_seconds
        self._send({
            "id": 1,
            "method": "session/create",
            "params": {
                "workspace": {"workspacePath": workspace, "workspaceKey": workspace},
                "mode": mode,
            },
        })
        while True:
            if _time.monotonic() >= deadline:
                raise ZCodeProtocolError("TURN_DEADLINE_EXCEEDED")
            line = self._transport.read_line(self._read_timeout)
            if line is None:
                if not self._transport.alive():
                    raise ZCodeProtocolError("CHILD_EXITED")
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                raise ZCodeProtocolError("PROTOCOL_LINE_MALFORMED") from None
            if not isinstance(message, dict):
                raise ZCodeProtocolError("PROTOCOL_LINE_MALFORMED")

            method = message.get("method")
            mid = message.get("id")
            if method == "session/requestRuntimePreferences" and mid is not None:
                self._send({"id": mid, "result": {"nativeSearchEnhancementsEnabled": False}})
                continue
            if method == "interaction/requestPermission" and mid is not None:
                # READ_ONLY policy: permission requests are denied, never granted.
                self._send({"id": mid, "result": {"approved": False}})
                continue

            if mid == 1 and session_id is None:
                if "error" in message:
                    raise ZCodeProtocolError("SESSION_CREATE_FAILED")
                result = message.get("result")
                session = result.get("session") if isinstance(result, dict) else None
                if not (isinstance(session, dict) and isinstance(session.get("sessionId"), str)):
                    raise ZCodeProtocolError("SESSION_CREATE_FAILED")
                session_id = session["sessionId"]
                self._send({
                    "id": 2,
                    "method": "session/subscribe",
                    "params": {
                        "sessionId": session_id,
                        "deliveryKind": "desktop-continuous",
                        "includeSnapshot": True,
                        "afterSeq": 0,
                    },
                })
                continue
            if mid == 2 and session_id is not None and not subscribed:
                if "error" in message:
                    raise ZCodeProtocolError("SUBSCRIBE_FAILED")
                subscribed = True
                if thought_level is not None:
                    self._send({
                        "id": 4,
                        "method": "session/setThoughtLevel",
                        "params": {"sessionId": session_id, "thoughtLevel": thought_level},
                    })
                else:
                    self._send({
                        "id": 3,
                        "method": "session/send",
                        "params": {"sessionId": session_id, "content": prompt},
                    })
                    prompt_sent = True
                continue
            if mid == 4 and session_id is not None and not prompt_sent:
                # advisory: a failed thought level still sends the prompt
                self._send({
                    "id": 3,
                    "method": "session/send",
                    "params": {"sessionId": session_id, "content": prompt},
                })
                prompt_sent = True
                continue
            if mid == 3 and "error" in message:
                raise ZCodeProtocolError("PROMPT_SEND_REJECTED")

            if method == "session/event":
                params = message.get("params")
                if not isinstance(params, dict):
                    continue
                event_type = params.get("type")
                payload = params.get("payload")
                if event_type == "model.streaming" and isinstance(payload, dict):
                    if payload.get("kind") == "text_delta" and isinstance(payload.get("delta"), str):
                        delta = payload["delta"]
                        received += len(delta.encode("utf-8"))
                        if received > self._max_response_bytes:
                            raise ZCodeProtocolError("RESPONSE_BUDGET_EXCEEDED")
                        deltas.append(delta)
                elif event_type == "turn.completed":
                    return ZCodeProtocolTurn(
                        response_text="".join(deltas),
                        session_id=session_id,
                        turn_completed=True,
                        bytes_received=received,
                    )
                elif event_type == "turn.failed":
                    raise ZCodeProtocolError("TURN_FAILED")
