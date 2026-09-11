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


_RUNTIME_MODEL_REVISION_RE = re.compile(r"^zcode-runtime-v1:[0-9a-f]{64}$")
_RUNTIME_ENV_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_RUNTIME_MODEL_MAX_JSON_BYTES = 8192


@dataclass(frozen=True, slots=True)
class ZCodeRuntimeModel:
    """Narrow, non-secret projection of Conductor provider authority.

    This is intentionally not a second provider configuration model. It is the
    minimum create-time ZCode 0.16.5 runtime projection needed to bind the
    actual app-server turn to the already-authorized Conductor provider/model/
    endpoint. Only the currently-proven Anthropic Messages shape is accepted;
    unsupported protocol families must fail closed in production assembly.
    """

    revision: str
    provider_id: str
    model_id: str
    base_url: str
    api_key_env: str

    def __post_init__(self) -> None:
        if not isinstance(self.revision, str) or not _RUNTIME_MODEL_REVISION_RE.fullmatch(self.revision):
            raise ValueError("runtime model revision is invalid")
        for field_name in ("provider_id", "model_id"):
            value = getattr(self, field_name)
            if (
                not isinstance(value, str)
                or not value.strip()
                or value != value.strip()
                or len(value) > 128
                or "\x00" in value
            ):
                raise ValueError(f"{field_name} is invalid")
        if not isinstance(self.base_url, str) or not self.base_url.strip() or self.base_url != self.base_url.strip():
            raise ValueError("base_url is invalid")
        from urllib.parse import urlsplit
        try:
            parsed = urlsplit(self.base_url)
            _ = parsed.port
        except ValueError as exc:
            raise ValueError("base_url is invalid") from exc
        if parsed.scheme.lower() not in {"http", "https"} or parsed.hostname is None:
            raise ValueError("base_url is invalid")
        if parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
            raise ValueError("base_url is invalid")
        if parsed.scheme.lower() == "http":
            host = parsed.hostname.casefold()
            loopback = host == "localhost"
            if not loopback:
                try:
                    import ipaddress
                    loopback = ipaddress.ip_address(host).is_loopback
                except ValueError:
                    loopback = False
            if not loopback:
                raise ValueError("external runtime model endpoints require HTTPS")
        if not isinstance(self.api_key_env, str) or not _RUNTIME_ENV_RE.fullmatch(self.api_key_env):
            raise ValueError("api_key_env is invalid")

    @property
    def model_ref(self) -> dict[str, str]:
        return {"providerId": self.provider_id, "modelId": self.model_id}

    def as_dict(self) -> dict[str, object]:
        return {
            "revision": self.revision,
            "generatedAt": 0,
            "model": self.model_ref,
            "provider": {
                "providerId": self.provider_id,
                "kind": "anthropic",
                "apiFormat": "anthropic-messages",
                "source": "ephemeral",
                "baseURL": self.base_url,
                "apiKey": {"source": "env", "name": self.api_key_env},
                "apiKeyRequired": True,
                "models": [{"modelId": self.model_id}],
            },
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, text: str) -> "ZCodeRuntimeModel":
        if (
            not isinstance(text, str)
            or not text
            or "\x00" in text
            or len(text.encode("utf-8")) > _RUNTIME_MODEL_MAX_JSON_BYTES
        ):
            raise ValueError("runtime model metadata is invalid")
        def _unique_object(pairs):
            obj = {}
            for key, value in pairs:
                if key in obj:
                    raise ValueError("duplicate runtime model metadata key")
                obj[key] = value
            return obj

        try:
            doc = json.loads(text, object_pairs_hook=_unique_object)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError("runtime model metadata is invalid") from exc
        if not isinstance(doc, dict) or set(doc) != {"revision", "generatedAt", "model", "provider"}:
            raise ValueError("runtime model metadata is invalid")
        if doc.get("generatedAt") != 0:
            raise ValueError("runtime model metadata is invalid")
        model = doc.get("model")
        provider = doc.get("provider")
        if not isinstance(model, dict) or set(model) != {"providerId", "modelId"}:
            raise ValueError("runtime model metadata is invalid")
        if not isinstance(provider, dict) or set(provider) != {
            "providerId", "kind", "apiFormat", "source", "baseURL",
            "apiKey", "apiKeyRequired", "models",
        }:
            raise ValueError("runtime model metadata is invalid")
        api_key = provider.get("apiKey")
        models = provider.get("models")
        base_url = provider.get("baseURL")
        if (
            provider.get("providerId") != model.get("providerId")
            or provider.get("kind") != "anthropic"
            or provider.get("apiFormat") != "anthropic-messages"
            or provider.get("source") != "ephemeral"
            or provider.get("apiKeyRequired") is not True
            or not isinstance(base_url, str)
            or not isinstance(api_key, dict)
            or set(api_key) != {"source", "name"}
            or api_key.get("source") != "env"
            or not isinstance(api_key.get("name"), str)
            or not isinstance(models, list)
            or len(models) != 1
            or not isinstance(models[0], dict)
            or set(models[0]) != {"modelId"}
            or models[0].get("modelId") != model.get("modelId")
        ):
            raise ValueError("runtime model metadata is invalid")
        return cls(
            revision=doc["revision"],
            provider_id=model["providerId"],
            model_id=model["modelId"],
            base_url=base_url,
            api_key_env=api_key["name"],
        )


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
        runtime_model: ZCodeRuntimeModel | None = None,
        deadline_seconds: float = 300.0,
    ) -> ZCodeProtocolTurn:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must not be blank")
        if mode not in {"plan", "build"}:
            raise ValueError("mode is invalid")
        if thought_level not in (None, "min", "low", "medium", "high", "max"):
            raise ValueError("thought_level is invalid")
        if runtime_model is not None and not isinstance(runtime_model, ZCodeRuntimeModel):
            raise ValueError("runtime_model must be a ZCodeRuntimeModel or None")
        if deadline_seconds <= 0:
            raise ValueError("deadline is invalid")

        session_id: str | None = None
        deltas: list[str] = []
        received = 0
        subscribed = False
        prompt_sent = False

        import time as _time

        deadline = _time.monotonic() + deadline_seconds
        create_params: dict[str, object] = {
            "workspace": {"workspacePath": workspace, "workspaceKey": workspace},
            "mode": mode,
        }
        if runtime_model is not None:
            # The full ephemeral provider definition removes ambient ZCode
            # provider/default-model authority. The API-key VALUE is absent:
            # ZCode resolves only the accepted env-var name in the child.
            create_params["runtimeModel"] = runtime_model.as_dict()
            create_params["model"] = runtime_model.model_ref
        self._send({
            "id": 1,
            "method": "session/create",
            "params": create_params,
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
                if runtime_model is not None:
                    settings = result.get("settings") if isinstance(result, dict) else None
                    model_settings = settings.get("model") if isinstance(settings, dict) else None
                    current_model = model_settings.get("current") if isinstance(model_settings, dict) else None
                    if not isinstance(current_model, dict):
                        raise ZCodeProtocolError("SESSION_MODEL_ATTESTATION_MISSING")
                    if (
                        current_model.get("providerId") != runtime_model.provider_id
                        or current_model.get("modelId") != runtime_model.model_id
                    ):
                        raise ZCodeProtocolError("SESSION_MODEL_MISMATCH")
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
