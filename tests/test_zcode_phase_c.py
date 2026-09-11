"""WO-P1-158 Phase C — ZCode protocol/helper proofs (no live traffic).

Protocol driver: bounded ops over an already-started transport only — no
spawn/start/stop/kill surface; typed bounded errors that redact secret-shaped
detail; 64 KiB response budget with exact-boundary behavior. Helper contract:
allowlisted argv grammar (prompt can never appear), PID-reuse-proof identity
matching, strict identity-document parsing, pre-spawn budget validation.
"""

from __future__ import annotations

import json
import time
from collections import deque

import pytest

from a_conductor.zcode_protocol import (
    ZCODE_MAX_RESPONSE_BYTES,
    ZCodeProtocolDriver,
    ZCodeProtocolError,
    ZCodeRuntimeModel,
)
from a_conductor.zcode_supervised_helper import (
    ZCodeChildIdentity,
    parse_child_identity_document,
    serialize_child_identity_document,
    target_argv_sha256,
    validate_app_server_argv,
    validate_output_budget,
)


class ScriptedTransport:
    def __init__(self, script):
        self._script = deque(script)
        self.sent: list[str] = []

    def send_line(self, text):
        self.sent.append(text)

    def read_line(self, timeout_seconds):
        if not self._script:
            return None
        item = self._script.popleft()
        if isinstance(item, Exception):
            raise item
        return item

    def alive(self):
        return True


def _create(session_id="sess-1"):
    return json.dumps({"id": 1, "result": {"session": {"sessionId": session_id}}})


def _prefs():
    return json.dumps({"id": 100, "method": "session/requestRuntimePreferences"})


def _subscribe_ok():
    return json.dumps({"id": 2, "result": {"ok": True}})


def _thought_ok():
    return json.dumps({"id": 4, "result": {"ok": True}})


def _delta(text):
    return json.dumps({
        "method": "session/event",
        "params": {"type": "model.streaming", "payload": {"kind": "text_delta", "delta": text}},
    })


def _completed():
    return json.dumps({"method": "session/event", "params": {"type": "turn.completed"}})


def _turn_failed():
    return json.dumps({"method": "session/event", "params": {"type": "turn.failed"}})


def _drive(script, **turn_kwargs):
    transport = ScriptedTransport(script)
    driver = ZCodeProtocolDriver(transport)
    turn_kwargs.setdefault("thought_level", None)
    turn_kwargs.setdefault("deadline_seconds", 10)
    turn = driver.run_turn("say OK", workspace="A:/fake", **turn_kwargs)
    return transport, turn


# ---------------- happy paths ----------------

def _runtime_model(provider_id="provider-a", model_id="glm-5.3"):
    return ZCodeRuntimeModel(
        revision="zcode-runtime-v1:" + "a" * 64,
        provider_id=provider_id,
        model_id=model_id,
        base_url="https://provider.example.test/anthropic",
        api_key_env="ANTHROPIC_API_KEY",
    )


def _create_with_model(provider_id="provider-a", model_id="glm-5.3", session_id="sess-1"):
    return json.dumps({
        "id": 1,
        "result": {
            "session": {"sessionId": session_id},
            "settings": {
                "model": {
                    "current": {"providerId": provider_id, "modelId": model_id},
                    "available": [],
                }
            },
        },
    })


def test_authorized_runtime_model_is_materialized_in_session_create():
    runtime_model = _runtime_model()
    transport = ScriptedTransport([
        _create_with_model(), _prefs(), _subscribe_ok(), _delta("OK"), _completed()
    ])
    driver = ZCodeProtocolDriver(transport)
    turn = driver.run_turn(
        "say OK",
        workspace="A:/fake",
        runtime_model=runtime_model,
        deadline_seconds=10,
    )
    assert turn.turn_completed
    messages = [json.loads(line) for line in transport.sent]
    create = messages[0]
    assert create["method"] == "session/create"
    assert create["params"]["runtimeModel"] == runtime_model.as_dict()
    assert create["params"]["model"] == runtime_model.model_ref
    wire = json.dumps(create, sort_keys=True)
    assert "credential-value-must-never-appear" not in wire
    assert wire.count("ANTHROPIC_API_KEY") == 1


def test_runtime_model_mismatch_fails_before_prompt_send():
    runtime_model = _runtime_model()
    transport = ScriptedTransport([
        _create_with_model(provider_id="provider-b", model_id="other-model"),
    ])
    driver = ZCodeProtocolDriver(transport)
    with pytest.raises(ZCodeProtocolError) as exc:
        driver.run_turn(
            "must-not-send",
            workspace="A:/fake",
            runtime_model=runtime_model,
            deadline_seconds=10,
        )
    assert exc.value.code == "SESSION_MODEL_MISMATCH"
    messages = [json.loads(line) for line in transport.sent]
    assert not any(message.get("method") == "session/send" for message in messages)


def test_runtime_model_transport_round_trip_is_non_secret():
    runtime_model = _runtime_model()
    encoded = runtime_model.to_json()
    assert "credential-value-must-never-appear" not in encoded
    assert '"source":"env"' in encoded
    assert ZCodeRuntimeModel.from_json(encoded) == runtime_model


@pytest.mark.parametrize(
    ("needle", "replacement"),
    (
        ('"provider":{', '"provider":{"providerId":"shadow"},"provider":{'),
        (
            '"baseURL":"https://provider.example.test/anthropic"',
            '"baseURL":"https://shadow.invalid","baseURL":"https://provider.example.test/anthropic"',
        ),
        ('"modelId":"glm-5.3"', '"modelId":"shadow-model","modelId":"glm-5.3"'),
    ),
)
def test_runtime_model_transport_rejects_duplicate_object_keys(needle, replacement):
    encoded = _runtime_model().to_json()
    duplicated = encoded.replace(needle, replacement, 1)
    assert duplicated != encoded
    with pytest.raises(ValueError, match="runtime model metadata is invalid"):
        ZCodeRuntimeModel.from_json(duplicated)


def test_runtime_model_transport_rejects_inline_secret_shape():
    doc = _runtime_model().as_dict()
    doc["provider"]["apiKey"] = {
        "source": "inline", "value": "credential-value-must-never-appear"
    }
    with pytest.raises(ValueError, match="runtime model metadata is invalid"):
        ZCodeRuntimeModel.from_json(json.dumps(doc))


def test_runtime_model_missing_attestation_fails_before_prompt_send():
    runtime_model = _runtime_model()
    transport = ScriptedTransport([_create()])
    driver = ZCodeProtocolDriver(transport)
    with pytest.raises(ZCodeProtocolError) as exc:
        driver.run_turn(
            "must-not-send",
            workspace="A:/fake",
            runtime_model=runtime_model,
            deadline_seconds=10,
        )
    assert exc.value.code == "SESSION_MODEL_ATTESTATION_MISSING"
    messages = [json.loads(line) for line in transport.sent]
    assert not any(message.get("method") == "session/send" for message in messages)


def test_runtime_model_rejects_non_loopback_cleartext_endpoint():
    with pytest.raises(ValueError, match="external runtime model endpoints require HTTPS"):
        ZCodeRuntimeModel(
            revision="zcode-runtime-v1:" + "a" * 64,
            provider_id="provider-a",
            model_id="glm-5.3",
            base_url="http://provider.example.test/anthropic",
            api_key_env="ANTHROPIC_API_KEY",
        )


def test_full_protocol_happy_path_without_thought():
    transport, turn = _drive([_create(), _prefs(), _subscribe_ok(), _delta("O"), _delta("K"), _completed()])
    assert turn.turn_completed and turn.response_text == "OK" and turn.session_id == "sess-1"
    messages = [json.loads(line) for line in transport.sent]
    assert messages[0]["method"] == "session/create"
    prefs = next(m for m in messages if m.get("id") == 100)
    assert prefs["result"] == {"nativeSearchEnhancementsEnabled": False}
    send = next(m for m in messages if m.get("method") == "session/send")
    assert send["params"]["content"] == "say OK"


def test_thought_level_advisory_failure_still_sends_prompt():
    transport, turn = _drive(
        [_create(), _prefs(), _subscribe_ok(),
         json.dumps({"id": 4, "error": {"message": "unsupported"}}),
         _delta("OK"), _completed()],
        thought_level="max",
    )
    assert turn.turn_completed and turn.response_text == "OK"


def test_permission_requests_are_denied():
    transport, turn = _drive(
        [_create(), _prefs(), _subscribe_ok(),
         json.dumps({"id": 101, "method": "interaction/requestPermission"}),
         _delta("OK"), _completed()],
    )
    denial = next(
        json.loads(line) for line in transport.sent
        if json.loads(line).get("id") == 101
    )
    assert denial["result"] == {"approved": False}
    assert turn.turn_completed


# ---------------- typed failures ----------------

def test_session_create_failure_is_typed():
    with pytest.raises(ZCodeProtocolError) as exc:
        _drive([json.dumps({"id": 1, "error": {"message": "nope"}})])
    assert exc.value.code == "SESSION_CREATE_FAILED"


def test_error_detail_secrets_are_redacted():
    err = ZCodeProtocolError("TURN_FAILED", "api key=sk-ant-abcdefghij123456 failed")
    assert "sk-ant" not in str(err.detail)
    assert err.detail == "[REDACTED]"


def test_error_codes_are_bounded():
    with pytest.raises(ValueError):
        ZCodeProtocolError("bad code!", "x")
    with pytest.raises(ValueError):
        ZCodeProtocolError("A" * 100)


def test_malformed_line_is_typed():
    with pytest.raises(ZCodeProtocolError) as exc:
        _drive(["not json"])
    assert exc.value.code == "PROTOCOL_LINE_MALFORMED"


def test_child_exit_is_typed():
    class DeadTransport(ScriptedTransport):
        def alive(self):
            return False

    transport = DeadTransport([])
    driver = ZCodeProtocolDriver(transport)
    with pytest.raises(ZCodeProtocolError) as exc:
        driver.run_turn("say OK", workspace="A:/fake")
    assert exc.value.code == "CHILD_EXITED"


def test_turn_failed_is_typed():
    with pytest.raises(ZCodeProtocolError) as exc:
        _drive([_create(), _prefs(), _subscribe_ok(), _turn_failed()])
    assert exc.value.code == "TURN_FAILED"


# ---------------- output budget ----------------

def test_exact_cap_passes_and_one_byte_over_fails():
    chunk = "x" * 1024
    script_at_cap = [_create(), _prefs(), _subscribe_ok()] + [_delta(chunk)] * 64 + [_completed()]
    _, turn = _drive(script_at_cap)
    assert turn.bytes_received == 64 * 1024  # exact cap passes

    script_over = [_create(), _prefs(), _subscribe_ok()] + [_delta(chunk)] * 65
    with pytest.raises(ZCodeProtocolError) as exc:
        _drive(script_over)
    assert exc.value.code == "RESPONSE_BUDGET_EXCEEDED"


def test_multibyte_byte_boundary_is_byte_accurate():
    delta = "é" * 100  # 200 bytes UTF-8 per delta
    driver_script = [_create(), _prefs(), _subscribe_ok()]
    # 329 deltas * 200B = 65,800 bytes > 64 KiB -> fails on the byte boundary
    driver_script += [_delta(delta)] * 329
    with pytest.raises(ZCodeProtocolError) as exc:
        _drive(driver_script, deadline_seconds=10)
    assert exc.value.code == "RESPONSE_BUDGET_EXCEEDED"
    # exact pass: 163 deltas * 200B = 32,600 bytes stays inside the budget
    _, turn = _drive(
        [_create(), _prefs(), _subscribe_ok()] + [_delta(delta)] * 163 + [_completed()],
        deadline_seconds=10,
    )
    assert turn.bytes_received == 163 * 200


def test_driver_cap_cannot_exceed_production_ceiling():
    with pytest.raises(ValueError):
        ZCodeProtocolDriver(ScriptedTransport([]), max_response_bytes=ZCODE_MAX_RESPONSE_BYTES + 1)


# ---------------- lifecycle-free proof ----------------

def test_protocol_module_has_no_lifecycle_surface():
    import inspect
    from a_conductor import zcode_protocol as module
    source = inspect.getsource(module)
    # strip the module docstring: it DOCUMENTS the absence of lifecycle imports
    source = source.split('"""', 2)[2] if source.count('"""') >= 2 else source
    for forbidden in (
        "import subprocess", "import os", "subprocess.", "Popen", "os.kill",
        "terminate(", ".kill(", "CreateProcess", "taskkill", "Stop-Process",
    ):
        assert forbidden not in source, forbidden
    driver_attrs = {
        name for name in dir(ZCodeProtocolDriver) if not name.startswith("__")
    }
    assert not driver_attrs & {"start", "stop", "spawn", "terminate", "kill"}


# ---------------- helper contract ----------------

ARGV = (r"C:\ZCode\ZCode.exe", r"C:\ZCode\resources\glm\zcode.cjs",
        "app-server", "--stdio", "--surface", "desktop")


def test_argv_grammar_rejects_prompt_content_and_extras():
    assert validate_app_server_argv(ARGV, executable=ARGV[0], bundle_js=ARGV[1])
    assert not validate_app_server_argv(ARGV + ("--prompt", "steal this"), executable=ARGV[0], bundle_js=ARGV[1])
    assert not validate_app_server_argv(("other.exe",) + ARGV[1:], executable=ARGV[0], bundle_js=ARGV[1])
    assert not validate_app_server_argv(ARGV[:5], executable=ARGV[0], bundle_js=ARGV[1])


def test_identity_round_trip_and_strict_document_parsing():
    identity = ZCodeChildIdentity(
        child_pid=4242, child_created_epoch_ms=1788490277831,
        executable=ARGV[0], parent_pid=100, target_argv_sha256=target_argv_sha256(ARGV),
        execution_id="exec-0123456789abcdef",
    )
    document = parse_child_identity_document(json.loads(serialize_child_identity_document(identity)))
    assert document == identity
    # smuggled prompt/secret key rejects
    bad = identity.as_dict()
    bad["prompt"] = "leak"
    with pytest.raises(ValueError):
        parse_child_identity_document(bad)
    with pytest.raises(ValueError):
        parse_child_identity_document("not-a-mapping")
    with pytest.raises(ValueError):
        wrong_schema = identity.as_dict()
        wrong_schema["schema"] = "other/1"
        parse_child_identity_document(wrong_schema)


def test_pid_reuse_rejected_by_creation_time():
    base = ZCodeChildIdentity(
        child_pid=500, child_created_epoch_ms=1000, executable=ARGV[0],
        parent_pid=1, target_argv_sha256=target_argv_sha256(ARGV),
        execution_id="exec-0123456789abcdef",
    )
    assert base.matches(ZCodeChildIdentity(
        child_pid=500, child_created_epoch_ms=1000, executable=ARGV[0],
        parent_pid=1, target_argv_sha256=base.target_argv_sha256,
        execution_id=base.execution_id,
    ))
    reused = ZCodeChildIdentity(
        child_pid=500, child_created_epoch_ms=9999, executable=ARGV[0],
        parent_pid=1, target_argv_sha256=base.target_argv_sha256,
        execution_id=base.execution_id,
    )
    assert not base.matches(reused)  # same PID, different creation time = MISMATCH


def test_output_budget_validated_before_spawn():
    assert validate_output_budget(64 * 1024) == 64 * 1024
    with pytest.raises(ValueError, match="ZCODE_OUTPUT_BUDGET_UNSUPPORTED"):
        validate_output_budget(64 * 1024 + 1)
    with pytest.raises(ValueError, match="ZCODE_OUTPUT_BUDGET_UNSUPPORTED"):
        validate_output_budget(0)


def test_deadline_is_enforced():
    class SlowTransport(ScriptedTransport):
        def read_line(self, timeout_seconds):
            time.sleep(0.02)
            return None

    driver = ZCodeProtocolDriver(SlowTransport([]), read_timeout_seconds=0.001)
    with pytest.raises(ZCodeProtocolError) as exc:
        driver.run_turn("say OK", workspace="A:/fake", deadline_seconds=0.05)
    assert exc.value.code in {"TURN_DEADLINE_EXCEEDED", "CHILD_EXITED"}
