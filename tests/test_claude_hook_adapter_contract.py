"""WO-P1-261 — Claude Code Hook Adapter v1 offline conformance.

Deterministic, offline-only tests for the mapping contract in
docs/contracts/claude-hook-adapter-v1.md against the Hook Contract v1
schema (docs/contracts/hook-contract-v1.schema.json), driven exclusively
by tests/fixtures/hook_adapters/claude/**.

The reference mapper below is test-local by design: WO-P1-261 adds no
src/runtime code. No network, no live CLI, no MCP.
"""

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs" / "contracts" / "hook-contract-v1.schema.json"
ADAPTER_DOC = ROOT / "docs" / "contracts" / "claude-hook-adapter-v1.md"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "hook_adapters" / "claude"
REGISTRY_PATH = FIXTURE_DIR / "capability_registry.json"
FRAMES_DIR = FIXTURE_DIR / "frames"
EXPECTED_DIR = FIXTURE_DIR / "expected"

DEPENDENCY_SHA = "f20fff006aad1e592b150ffdcb52ac331ec00a3a"
CONTRACT_MD_BLOB = "b4f98fb8f2ce35958b4e5cfc660eeb671c46d723"
CONTRACT_SCHEMA_BLOB = "23c5dc3035320dc288e376bd103d8e00409a9762"

ADAPTER_ID = "claude-hook-adapter"
ADAPTER_VERSION = "1.0.0"
PINNED_CONTRACT_VERSION = "1.0.0"
FIXTURE_VERSION = "0.0.0-fixture-a"
REAL_VERSION = "2.1.178"

DEVICE_ID = "device-fx-01"
HOST_OS = "windows"
CAPABILITY_OCCURRED_AT = "2026-09-19T08:00:00Z"
CAPABILITY_SUMMARY = "claude hook adapter capabilities"

FAKE_SECRET_CORPUS = (
    "sk-FAKE0000000000000000000000000000000000",
    "ghp_FAKE0000000000000000000000000000000",
    "xoxb-FAKE-000000000000000000000000",
    "AKIAFAKE0000000000",
    "FAKESESSIONCOOKIE=0000000000000000",
    "-----BEGIN FAKE PRIVATE KEY-----",
    "https://chat.example/FAKE/share/0000",
    "Bearer FAKE000000000000000000000000000",
)

SECRET_SHAPE_MARKERS = (
    "sk-",
    "ghp_",
    "xoxb-",
    "AKIA",
    "Bearer ",
    "BEGIN FAKE PRIVATE KEY",
    "FAKESESSIONCOOKIE",
    "/FAKE/share/",
)

FORBIDDEN_FIELDS = (
    "prompt",
    "messages",
    "transcript",
    "token",
    "api_key",
    "apikey",
    "secret",
    "secret_value",
    "password",
    "credential_value",
    "cookie",
    "share_url",
    "session_url",
    "argv",
    "command_line",
    "shell_command",
)

SUMMARY_VOCABULARY = frozenset(
    {
        "session started",
        "session ended",
        "prompt submitted",
        "tool execution before",
        "tool execution after",
        "tool execution failed",
        "subagent started",
        "subagent stopped",
        "agent turn stopped",
        CAPABILITY_SUMMARY,
    }
)

FAILURE_CODE_VOCABULARY = frozenset(
    {"NATIVE_TOOL_ERROR", "NATIVE_TIMEOUT", "NATIVE_PERMISSION_DENIED"}
)

IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
EVENT_ID_RE = re.compile(r"^hk-[0-9a-f]{32}$")
UTC_Z_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,9})?Z$")
EVENT_TYPE_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){1,2}$")
MAX_ENVELOPE_BYTES = 65536
BOUNDED_FILE_COUNT = 16


# ---------------------------------------------------------------------------
# Fixture loading helpers
# ---------------------------------------------------------------------------


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def schema() -> dict:
    return load_json(SCHEMA_PATH)


@pytest.fixture(scope="module")
def validator(schema) -> Draft202012Validator:
    return Draft202012Validator(schema)


@pytest.fixture(scope="module")
def registry() -> dict:
    return load_json(REGISTRY_PATH)


def frame_paths() -> list:
    return sorted(FRAMES_DIR.glob("*.json"))


def expected_paths() -> list:
    return sorted(EXPECTED_DIR.glob("*.json"))


def frames_with_outcome(outcome: str) -> list:
    return [p for p in frame_paths() if load_json(p)["expect_outcome"] == outcome]


# ---------------------------------------------------------------------------
# Reference mapper (test-local; production wiring is a later Work Order)
# ---------------------------------------------------------------------------


def _reject(code: str, detail: str, security_invalid: bool = False) -> dict:
    return {
        "outcome": "reject",
        "code": code,
        "detail": detail,
        "security_invalid": security_invalid,
    }


def _is_secret_shaped(value: str) -> bool:
    return any(marker in value for marker in SECRET_SHAPE_MARKERS) or any(
        item in value for item in FAKE_SECRET_CORPUS
    )


def _canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _command_digest(tool_ref: str, tool_payload) -> str:
    payload_sha = hashlib.sha256(
        _canonical_json(tool_payload).encode("utf-8")
    ).hexdigest()
    mixed = f"{tool_ref}:{payload_sha}".encode("utf-8")
    return hashlib.sha256(mixed).hexdigest()[:64]


def _format_utc(dt: datetime) -> str:
    dt = dt.astimezone(timezone.utc)
    base = dt.strftime("%Y-%m-%dT%H:%M:%S")
    micro = dt.microsecond
    if micro == 0:
        return base + "Z"
    if micro % 1000 == 0:
        return f"{base}.{micro // 1000:03d}Z"
    return f"{base}.{micro:06d}Z"


def _normalize_timestamp(raw) -> tuple:
    """Return (ok, formatted-or-detail). Ambiguous/unparseable fail closed."""
    if not isinstance(raw, str):
        return False, "timestamp-not-string"
    candidate = raw.strip()
    if candidate.endswith(("z", "Z")):
        candidate = candidate[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return False, "timestamp-unparseable"
    if parsed.tzinfo is None:
        return False, "timestamp-ambiguous"
    return True, _format_utc(parsed)


def _identifier_or_none(value):
    if isinstance(value, str) and IDENTIFIER_RE.match(value):
        return value
    return None


def _envelope_bytes(payload: dict) -> int:
    return len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))


def finalize_envelope(candidate: dict) -> dict:
    """Size + identity guard every produced envelope must pass (contract §10)."""
    if not EVENT_ID_RE.match(str(candidate.get("event_id", ""))):
        return _reject("HOOK_EVENT_INVALID", "event-id-invalid")
    if _envelope_bytes(candidate) > MAX_ENVELOPE_BYTES:
        return _reject("HOOK_EVENT_OVERSIZED", "envelope-over-max-bytes")
    return {"outcome": "envelope", "envelope": candidate}


def normalize_frame(
    payload: dict,
    *,
    registry: dict,
    event_id: str,
    device_id: str = DEVICE_ID,
    host_os: str = HOST_OS,
    contract_version: str = PINNED_CONTRACT_VERSION,
) -> dict:
    """Map one native-shaped fixture frame per the adapter contract."""
    if contract_version != PINNED_CONTRACT_VERSION:
        return _reject("HOOK_VERSION_UNSUPPORTED", "contract-version-unpinned")

    native_version = payload.get("native_version")
    entry = registry["versions"].get(native_version)
    if entry is None:
        return _reject("HOOK_ADAPTER_UNAVAILABLE", "native-version-unknown")

    discriminator_field = entry.get("discriminator_field")
    if not discriminator_field or entry.get("status") == "DISCOVERY_REQUIRED":
        return _reject("HOOK_ADAPTER_UNAVAILABLE", "discovery-required")

    frame = payload.get("frame", {})
    discriminator = frame.get(discriminator_field)
    binding = entry["native_bindings"].get(discriminator)
    if binding is None:
        return _reject("HOOK_ADAPTER_UNAVAILABLE", "mapping-unavailable")

    segments = binding["event_type"].split(".")
    domain, action = segments[0], segments[1]
    envelope = {
        "schema_version": PINNED_CONTRACT_VERSION,
        "event_id": event_id,
        "event_type": binding["event_type"],
        "hook_class": "OBSERVE",
        "phase": binding["phase"],
        "domain": domain,
        "action": action,
        "occurred_at": None,
        "source": "claude-code",
        "source_version": native_version,
        "device_id": device_id,
        "host_os": host_os,
        "privacy_class": binding["privacy_class"],
    }

    ok, formatted = _normalize_timestamp(frame.get("occurred_at"))
    if not ok:
        return _reject("HOOK_EVENT_INVALID", formatted)
    envelope["occurred_at"] = formatted

    correlation = _identifier_or_none(frame.get("session_ref"))
    if correlation is not None:
        if _is_secret_shaped(correlation):
            return _reject("HOOK_EVENT_INVALID", "secret-in-destination", True)
        envelope["correlation_id"] = correlation

    for source_key in ("turn_ref", "subagent_ref"):
        execution = _identifier_or_none(frame.get(source_key))
        if execution is not None:
            if _is_secret_shaped(execution):
                return _reject("HOOK_EVENT_INVALID", "secret-in-destination", True)
            envelope["execution_id"] = execution
            break

    model = _identifier_or_none(frame.get("model_ref"))
    if model is not None:
        if _is_secret_shaped(model):
            return _reject("HOOK_EVENT_INVALID", "secret-in-destination", True)
        envelope["model_id"] = model

    duration = frame.get("duration_ms")
    if isinstance(duration, int) and not isinstance(duration, bool) and duration >= 0:
        envelope["duration_ms"] = duration

    if envelope["event_type"].startswith("tool."):
        failure_code = frame.get("failure_code")
        if failure_code is not None:
            if failure_code not in FAILURE_CODE_VOCABULARY:
                return _reject("HOOK_EVENT_INVALID", "failure-code-outside-vocabulary")
            envelope["blocker_code"] = failure_code
        tool_ref = frame.get("tool_ref")
        tool_payload = frame.get("tool_payload")
        if isinstance(tool_ref, str) and tool_payload is not None:
            envelope["command_digest"] = _command_digest(tool_ref, tool_payload)

    envelope["summary"] = binding["summary_token"]
    return finalize_envelope(envelope)


def capability_event(
    registry: dict,
    native_version: str,
    *,
    event_id: str,
    device_id: str = DEVICE_ID,
    host_os: str = HOST_OS,
    occurred_at: str = CAPABILITY_OCCURRED_AT,
    contract_version: str = PINNED_CONTRACT_VERSION,
) -> dict:
    """Build the §6.1 capability-discovery event for a registry version."""
    if contract_version != PINNED_CONTRACT_VERSION:
        return _reject("HOOK_VERSION_UNSUPPORTED", "contract-version-unpinned")
    entry = registry["versions"][native_version]
    envelope = {
        "schema_version": PINNED_CONTRACT_VERSION,
        "event_id": event_id,
        "event_type": "transport.adapter_capabilities",
        "hook_class": "OBSERVE",
        "phase": "within",
        "domain": "transport",
        "action": "adapter_capabilities",
        "occurred_at": occurred_at,
        "source": "claude-code",
        "source_version": native_version,
        "device_id": device_id,
        "host_os": host_os,
        "privacy_class": "INTERNAL",
        "evidence_refs": ["docs/contracts/claude-hook-adapter-v1.md"],
        "summary": CAPABILITY_SUMMARY,
        "adapter": {
            "adapter_id": ADAPTER_ID,
            "adapter_version": ADAPTER_VERSION,
            "contract_version": PINNED_CONTRACT_VERSION,
            "emits": list(entry["emits"]),
            "redaction_policy": "fake-secret-corpus/1",
            "supports_sequence": False,
        },
    }
    return finalize_envelope(envelope)


def contract_doc_text() -> str:
    return ADAPTER_DOC.read_text(encoding="utf-8")


def contract_doc_flat() -> str:
    """Doc text with all whitespace collapsed, for wrap-tolerant phrase checks."""
    return re.sub(r"\s+", " ", contract_doc_text())


# ---------------------------------------------------------------------------
# Registry honesty and dependency pin
# ---------------------------------------------------------------------------


def test_registry_real_versions_carry_no_bindings_at_freeze(registry) -> None:
    real_entries = {
        version: entry
        for version, entry in registry["versions"].items()
        if entry["real_version"]
    }
    assert real_entries, "fixture registry must contain at least one real version"
    for version, entry in real_entries.items():
        assert entry["native_bindings"] == {}, version
        assert entry.get("discriminator_field") is None, version
        assert entry["status"] == "DISCOVERY_REQUIRED", version
        assert entry["emits"] == ["transport.adapter_capabilities"], version
        assert entry["evidence"], version


def test_registry_fixture_entry_is_marked_synthetic(registry) -> None:
    entry = registry["versions"][FIXTURE_VERSION]
    assert entry["real_version"] is False
    assert entry["status"] == "FIXTURE_ONLY"
    assert entry["discriminator_field"] == "fixture_event"
    assert set(entry["native_bindings"]) == {
        "FxSessionStart",
        "FxSessionEnd",
        "FxUserPrompt",
        "FxToolPre",
        "FxToolPost",
        "FxToolFail",
        "FxSubagentStart",
        "FxSubagentStop",
        "FxAgentStop",
    }
    expected_emits = {b["event_type"] for b in entry["native_bindings"].values()}
    expected_emits.add("transport.adapter_capabilities")
    assert set(entry["emits"]) == expected_emits


def test_registry_contains_no_secret_corpus() -> None:
    text = REGISTRY_PATH.read_text(encoding="utf-8")
    for item in FAKE_SECRET_CORPUS:
        assert item not in text
    assert "FXBAIT" not in text


def test_dependency_pin_recorded_in_contract_doc() -> None:
    text = contract_doc_text()
    assert DEPENDENCY_SHA in text
    assert CONTRACT_MD_BLOB in text
    assert CONTRACT_SCHEMA_BLOB in text
    assert "hook-contract-v1.schema.json" in text
    assert SCHEMA_PATH.exists()


def test_contract_doc_records_local_evidence_without_native_names() -> None:
    text = contract_doc_flat()
    assert REAL_VERSION in text
    assert "--include-hook-events" in text
    assert "DISCOVERY_REQUIRED" in text
    assert "asserts NO native event name" in text
    assert "fake-secret-corpus/1" in text


def test_contract_doc_mapping_table_matches_registry(registry) -> None:
    text = contract_doc_text()
    for binding in registry["versions"][FIXTURE_VERSION]["native_bindings"].values():
        assert binding["event_type"] in text
        assert binding["summary_token"] in text


def test_contract_doc_forbids_guard_and_command_and_delegates_ordering() -> None:
    text = contract_doc_flat()
    assert "MUST NOT emit GUARD or COMMAND envelopes" in text
    assert "does not invent global sequence or clock authority" in text
    assert "supports_sequence: false" in text
    assert "no fallback vocabulary" in text.lower() or "no default mapping" in text


# ---------------------------------------------------------------------------
# Fixture tree hygiene
# ---------------------------------------------------------------------------


def test_fixture_tree_is_bounded_and_strict_utf8() -> None:
    all_files = [REGISTRY_PATH, *frame_paths(), *expected_paths()]
    for path in all_files:
        path.read_text(encoding="utf-8")  # strict UTF-8 decode
    assert len(frame_paths()) <= BOUNDED_FILE_COUNT
    assert len(expected_paths()) <= BOUNDED_FILE_COUNT


def test_every_frame_declares_its_expected_outcome() -> None:
    for path in frame_paths():
        payload = load_json(path)
        assert payload["expect_outcome"] in {"envelope", "reject"}, path.name
        assert isinstance(payload["contains_redaction_bait"], bool), path.name
        if payload["expect_outcome"] == "reject":
            assert payload["expect_code"], path.name
        else:
            assert (EXPECTED_DIR / path.name).exists(), path.name


def test_corpus_confined_to_marked_bait_frames() -> None:
    carrying = set()
    for path in frame_paths():
        text = path.read_text(encoding="utf-8")
        if any(item in text for item in FAKE_SECRET_CORPUS):
            carrying.add(path.name)
            assert load_json(path)["contains_redaction_bait"] is True, path.name
    assert carrying == {
        "fx_user_prompt.json",
        "fx_tool_fail.json",
        "fx_secret_identifier.json",
        "fx_secret_dropped.json",
    }


# ---------------------------------------------------------------------------
# Golden mapping: frames -> expected envelopes, rejects -> typed codes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("frame_path", frames_with_outcome("envelope"))
def test_valid_frames_produce_expected_envelopes(
    validator, registry, frame_path
) -> None:
    payload = load_json(frame_path)
    expected = load_json(EXPECTED_DIR / frame_path.name)
    result = normalize_frame(payload, registry=registry, event_id=expected["event_id"])
    assert result["outcome"] == "envelope", result
    assert result["envelope"] == expected
    assert validator.is_valid(result["envelope"])
    assert UTC_Z_RE.match(result["envelope"]["occurred_at"])


@pytest.mark.parametrize("frame_path", frames_with_outcome("reject"))
def test_invalid_frames_reject_typed_without_envelope(registry, frame_path) -> None:
    payload = load_json(frame_path)
    result = normalize_frame(
        payload, registry=registry, event_id="hk-" + "ff" * 16
    )
    assert result["outcome"] == "reject", result
    assert result["code"] == payload["expect_code"], frame_path.name
    assert "envelope" not in result
    if payload.get("expect_security_invalid"):
        assert result["security_invalid"] is True


@pytest.mark.parametrize("expected_path", expected_paths())
def test_expected_files_are_schema_valid_and_observe_only(validator, expected_path) -> None:
    envelope = load_json(expected_path)
    assert validator.is_valid(envelope), expected_path.name
    assert envelope["hook_class"] == "OBSERVE"
    assert envelope["source"] == "claude-code"
    assert envelope["event_type"] == ".".join(
        [envelope["domain"], envelope["action"]]
    ) or envelope["event_type"].startswith(
        envelope["domain"] + "." + envelope["action"] + "."
    )
    assert EVENT_TYPE_RE.match(envelope["event_type"])
    assert UTC_Z_RE.match(envelope["occurred_at"])
    assert envelope["summary"] in SUMMARY_VOCABULARY
    assert "sequence" not in envelope
    assert "dedupe_key" not in envelope
    assert _envelope_bytes(envelope) <= MAX_ENVELOPE_BYTES
    for field in FORBIDDEN_FIELDS:
        assert field not in envelope


# ---------------------------------------------------------------------------
# Capability discovery
# ---------------------------------------------------------------------------


def test_capability_event_for_real_version_claims_nothing_unproven(
    validator, registry
) -> None:
    expected = load_json(EXPECTED_DIR / "capability_claude_2_1_178.json")
    result = capability_event(
        registry, REAL_VERSION, event_id=expected["event_id"]
    )
    assert result["outcome"] == "envelope"
    assert result["envelope"] == expected
    assert validator.is_valid(result["envelope"])
    adapter = expected["adapter"]
    assert adapter["emits"] == ["transport.adapter_capabilities"]
    assert adapter["supports_sequence"] is False
    assert adapter["redaction_policy"] == "fake-secret-corpus/1"
    assert adapter["contract_version"] == PINNED_CONTRACT_VERSION


def test_capability_event_for_fixture_version_lists_bound_mappings(
    validator, registry
) -> None:
    expected = load_json(EXPECTED_DIR / "capability_fixture.json")
    result = capability_event(
        registry, FIXTURE_VERSION, event_id=expected["event_id"]
    )
    assert result["outcome"] == "envelope"
    assert result["envelope"] == expected
    assert validator.is_valid(result["envelope"])
    assert set(expected["adapter"]["emits"]) == set(
        registry["versions"][FIXTURE_VERSION]["emits"]
    )


# ---------------------------------------------------------------------------
# Redaction guarantees
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("frame_path", frames_with_outcome("envelope"))
def test_no_corpus_or_bait_leak_from_any_mapped_frame(registry, frame_path) -> None:
    expected = load_json(EXPECTED_DIR / frame_path.name)
    serialized = json.dumps(expected, ensure_ascii=False)
    for item in FAKE_SECRET_CORPUS:
        assert item not in serialized, frame_path.name
    assert "FXBAIT" not in serialized, frame_path.name


def test_expected_tree_and_doc_carry_no_corpus() -> None:
    for path in expected_paths():
        text = path.read_text(encoding="utf-8")
        for item in FAKE_SECRET_CORPUS:
            assert item not in text, path.name
        assert "FXBAIT" not in text, path.name


def test_secret_in_dropped_field_produces_clean_envelope(registry) -> None:
    payload = load_json(FRAMES_DIR / "fx_secret_dropped.json")
    result = normalize_frame(
        payload, registry=registry, event_id="hk-" + "0a" * 16
    )
    assert result["outcome"] == "envelope", result
    serialized = json.dumps(result["envelope"], ensure_ascii=False)
    assert "ghp_FAKE" not in serialized
    assert "FXBAIT" not in serialized


def test_secret_in_destination_is_security_invalid(registry) -> None:
    payload = load_json(FRAMES_DIR / "fx_secret_identifier.json")
    result = normalize_frame(
        payload, registry=registry, event_id="hk-" + "0b" * 16
    )
    assert result == {
        "outcome": "reject",
        "code": "HOOK_EVENT_INVALID",
        "detail": "secret-in-destination",
        "security_invalid": True,
    }


# ---------------------------------------------------------------------------
# Version / capability mismatch — no silent fallback
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "frame_path", frames_with_outcome("envelope")
)
def test_real_version_never_uses_fixture_bindings(registry, frame_path) -> None:
    payload = load_json(frame_path)
    drifted = dict(payload, native_version=REAL_VERSION)
    result = normalize_frame(
        drifted, registry=registry, event_id="hk-" + "cc" * 16
    )
    assert result["outcome"] == "reject"
    assert result["code"] == "HOOK_ADAPTER_UNAVAILABLE"


def test_unknown_native_version_is_typed_unavailable(registry) -> None:
    payload = load_json(FRAMES_DIR / "fx_session_start.json")
    result = normalize_frame(
        dict(payload, native_version="9.9.9"),
        registry=registry,
        event_id="hk-" + "cd" * 16,
    )
    assert result == {
        "outcome": "reject",
        "code": "HOOK_ADAPTER_UNAVAILABLE",
        "detail": "native-version-unknown",
        "security_invalid": False,
    }


@pytest.mark.parametrize("bad_version", ["2.0.0", "1.1.0", "0.9.0", "1.0"])
def test_contract_version_mismatch_is_typed_unsupported(registry, bad_version) -> None:
    payload = load_json(FRAMES_DIR / "fx_session_start.json")
    result = normalize_frame(
        payload,
        registry=registry,
        event_id="hk-" + "ce" * 16,
        contract_version=bad_version,
    )
    assert result["code"] == "HOOK_VERSION_UNSUPPORTED"
    assert "envelope" not in result
    caps = capability_event(
        registry,
        FIXTURE_VERSION,
        event_id="hk-" + "cf" * 16,
        contract_version=bad_version,
    )
    assert caps["code"] == "HOOK_VERSION_UNSUPPORTED"


def test_ambiguous_and_unparseable_timestamps_fail_closed(registry) -> None:
    payload = load_json(FRAMES_DIR / "fx_ambiguous_timestamp.json")
    result = normalize_frame(
        payload, registry=registry, event_id="hk-" + "d0" * 16
    )
    assert result["outcome"] == "reject"
    assert result["code"] == "HOOK_EVENT_INVALID"
    assert result["detail"] == "timestamp-ambiguous"

    frame = json.loads(json.dumps(payload))
    frame["frame"]["occurred_at"] = "not-a-timestamp"
    result = normalize_frame(frame, registry=registry, event_id="hk-" + "d1" * 16)
    assert result["code"] == "HOOK_EVENT_INVALID"
    assert result["detail"] == "timestamp-unparseable"


def test_failure_code_outside_closed_vocabulary_rejected(registry) -> None:
    payload = load_json(FRAMES_DIR / "fx_bad_failure_code.json")
    result = normalize_frame(
        payload, registry=registry, event_id="hk-" + "d2" * 16
    )
    assert result == {
        "outcome": "reject",
        "code": "HOOK_EVENT_INVALID",
        "detail": "failure-code-outside-vocabulary",
        "security_invalid": False,
    }


# ---------------------------------------------------------------------------
# Identity reuse, ordering delegation, size guard
# ---------------------------------------------------------------------------


def test_retry_reuses_event_id_and_is_idempotent(registry) -> None:
    payload = load_json(FRAMES_DIR / "fx_tool_pre.json")
    event_id = "hk-" + "04" * 16
    first = normalize_frame(payload, registry=registry, event_id=event_id)
    second = normalize_frame(payload, registry=registry, event_id=event_id)
    assert first["outcome"] == second["outcome"] == "envelope"
    assert first["envelope"] == second["envelope"]
    assert first["envelope"]["event_id"] == event_id


def test_command_digest_is_derived_not_copied(registry) -> None:
    payload = load_json(FRAMES_DIR / "fx_tool_fail.json")
    result = normalize_frame(
        payload, registry=registry, event_id="hk-" + "06" * 16
    )
    envelope = result["envelope"]
    digest = envelope["command_digest"]
    assert re.match(r"^[0-9a-f]{16,128}$", digest)
    assert digest == _command_digest("FxBash", {"command": "curl https://chat.example/FAKE/share/0000"})
    serialized = json.dumps(envelope, ensure_ascii=False)
    assert "curl" not in serialized
    assert "FxBash" not in serialized
    assert "chat.example" not in serialized


def test_oversized_envelope_rejected_without_truncation() -> None:
    candidate = {
        "schema_version": PINNED_CONTRACT_VERSION,
        "event_id": "hk-" + "ee" * 16,
        "event_type": "execution.session_started",
        "hook_class": "OBSERVE",
        "phase": "within",
        "domain": "execution",
        "action": "session_started",
        "occurred_at": "2026-09-19T08:00:00Z",
        "source": "claude-code",
        "source_version": FIXTURE_VERSION,
        "device_id": "device-fx-01",
        "host_os": "windows",
        "privacy_class": "INTERNAL",
        "summary": "session started",
        "correlation_id": "c" * 70000,
    }
    assert _envelope_bytes(candidate) > MAX_ENVELOPE_BYTES
    result = finalize_envelope(candidate)
    assert result["outcome"] == "reject"
    assert result["code"] == "HOOK_EVENT_OVERSIZED"
    assert len(result.get("envelope", {}).get("correlation_id", "")) != 128


def test_invalid_event_id_rejected_at_finalize() -> None:
    result = finalize_envelope({"event_id": "not-an-event-id"})
    assert result["code"] == "HOOK_EVENT_INVALID"
