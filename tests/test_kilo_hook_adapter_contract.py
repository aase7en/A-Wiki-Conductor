"""WO-P1-262 - Kilo Hook Adapter v1 offline conformance suite.

Reference mapper + fixtures under tests/fixtures/hook_adapters/kilo/ prove
the adapter contract in docs/contracts/kilo-hook-adapter-v1.md against the
frozen Hook Contract v1 schema (dependency f20fff006aad1e592b150ffdcb52ac331ec00a3a).

Deterministic, offline only: no network, no MCP, no runtime, no live Kilo
process. All native records are fake, bounded, native-shaped fixtures.
"""

import hashlib
import itertools
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "hook_adapters" / "kilo"
SCHEMA_PATH = ROOT / "docs" / "contracts" / "hook-contract-v1.schema.json"
CONTRACT = ROOT / "docs" / "contracts" / "kilo-hook-adapter-v1.md"

# Shared fake-secret corpus, defined by docs/contracts/hook-contract-v1.md
# section 11 (fake-secret-corpus/1). Not secret; uniform leakage check.
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

MAX_ENVELOPE_BYTES = 65536

VERIFIED_KILO_FAMILY = re.compile(r"^7\.7\.\d+(?:[.-][0-9A-Za-z.-]+)?$")
CONTRACT_VERSION_LINE = re.compile(r"^1\.\d+\.\d+$")
TOOL_NAME = re.compile(r"^[A-Za-z0-9._-]{1,32}$")
STATUS_VOCABULARY = ("running", "completed", "failed")

CONTEXT = {
    "device_id": "device-01",
    "host_os": "windows",
    "harness_id": "kilo-cli",
    "expected_provider_model": "cointh-glm/glm-5.3",
    "adapter_source_version": "7.7.2",
    "capabilities_occurred_at": "2026-09-19T08:40:00Z",
}


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def deterministic_event_id_factory():
    counter = itertools.count()

    def factory() -> str:
        i = next(counter)
        return f"hk-{i:012x}4{i:03x}8{i:015x}"

    return factory


def normalize_timestamp(raw):
    text = raw.strip() if isinstance(raw, str) else None
    if text is None:
        return None
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return None
    if moment.tzinfo is None:
        return None
    moment = moment.astimezone(timezone.utc)
    if moment.microsecond:
        return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


class KiloHookAdapterHarness:
    """Deterministic reference mapper for kilo-hook-adapter-v1.

    Implements exactly the mapping, redaction, capability, and fail-closed
    mismatch rules declared in docs/contracts/kilo-hook-adapter-v1.md.
    """

    def __init__(self, capability, context=None, event_id_factory=None):
        self.capability = capability
        self.context = dict(CONTEXT if context is None else context)
        self._event_id_factory = event_id_factory or deterministic_event_id_factory()
        self._event_ids = {}

    def _event_id(self, dedupe_key: str) -> str:
        if dedupe_key not in self._event_ids:
            self._event_ids[dedupe_key] = self._event_id_factory()
        return self._event_ids[dedupe_key]

    def _emits(self, event_type: str) -> bool:
        return event_type in self.capability.get("emits", [])

    def _capability_event(self) -> dict:
        return {
            "schema_version": "1.0.0",
            "event_id": self._event_id(
                f"kilo:adapter-capabilities:{self.capability['adapter_version']}"
            ),
            "event_type": "transport.adapter_capabilities",
            "hook_class": "OBSERVE",
            "phase": "before",
            "domain": "transport",
            "action": "adapter_capabilities",
            "occurred_at": self.context["capabilities_occurred_at"],
            "source": "kilo",
            "source_version": self.context["adapter_source_version"],
            "device_id": self.context["device_id"],
            "host_os": self.context["host_os"],
            "privacy_class": "INTERNAL",
            "dedupe_key": f"kilo:adapter-capabilities:{self.capability['adapter_version']}",
            "adapter": self.capability,
        }

    def _base_envelope(self, meta, record, line_digest, line_no, occurred_at, event_type, phase, domain, action):
        session_id = record["sessionID"]
        return {
            "schema_version": "1.0.0",
            "event_id": self._event_id(f"kilo:{session_id}:{line_digest[:16]}"),
            "event_type": event_type,
            "hook_class": "OBSERVE",
            "phase": phase,
            "domain": domain,
            "action": action,
            "occurred_at": occurred_at,
            "source": "kilo",
            "source_version": meta["kilo_version"],
            "device_id": self.context["device_id"],
            "host_os": self.context["host_os"],
            "privacy_class": "INTERNAL",
            "harness_id": self.context["harness_id"],
            "model_id": meta["provider_model"],
            "correlation_id": session_id,
            "dedupe_key": f"kilo:{session_id}:{line_digest[:16]}",
            "evidence_refs": [f"{meta['evidence_base']}:L{line_no}"],
            "evidence_digest": line_digest,
        }

    def normalize_stream(self, meta, ndjson_text):
        events, reasons = [], []

        if self.capability is None:
            return [], ["HOOK_ADAPTER_UNAVAILABLE:missing_capability_document"]
        contract_version = self.capability.get("contract_version", "")
        if not CONTRACT_VERSION_LINE.match(contract_version):
            return [], [f"HOOK_VERSION_UNSUPPORTED:contract_version:{contract_version}"]
        kilo_version = meta.get("kilo_version", "")
        if not VERIFIED_KILO_FAMILY.match(kilo_version):
            return [], [
                f"HOOK_VERSION_UNSUPPORTED:KILO_VERSION_UNSUPPORTED:{kilo_version}"
            ]
        if meta.get("provider_model") != self.context["expected_provider_model"]:
            return [], [
                "HOOK_ADAPTER_UNAVAILABLE:KILO_PROVIDER_MODEL_MISMATCH:"
                f"{meta.get('provider_model')}"
            ]

        events.append(self._capability_event())

        for line_no, line in enumerate(ndjson_text.splitlines(), start=1):
            if not line.strip():
                continue
            mapped = self._normalize_record(meta, line, line_no)
            if isinstance(mapped, dict):
                events.append(mapped)
            else:
                reasons.append(mapped)

        return events, reasons

    def _normalize_record(self, meta, line, line_no):
        line_digest = sha256_hex(line.strip())
        try:
            record = json.loads(line)
        except ValueError:
            return "HOOK_EVENT_INVALID:KILO_RECORD_INVALID:not_json"
        if not isinstance(record, dict):
            return "HOOK_EVENT_INVALID:KILO_RECORD_INVALID:not_object"
        session_id = record.get("sessionID")
        if not isinstance(session_id, str) or not session_id:
            return "HOOK_EVENT_INVALID:KILO_RECORD_INVALID:missing_session_id"
        occurred_at = normalize_timestamp(record.get("timestamp"))
        if occurred_at is None:
            return "HOOK_EVENT_INVALID:KILO_RECORD_INVALID:timestamp"

        native_type = record.get("type")

        if native_type == "step_start":
            if not self._emits("execution.step_start"):
                return "HOOK_ADAPTER_UNAVAILABLE:TYPE_NOT_EMITTED:execution.step_start"
            return self._base_envelope(
                meta, record, line_digest, line_no, occurred_at,
                "execution.step_start", "within", "execution", "step_start",
            )

        if native_type == "text":
            if not self._emits("execution.message"):
                return "HOOK_ADAPTER_UNAVAILABLE:TYPE_NOT_EMITTED:execution.message"
            envelope = self._base_envelope(
                meta, record, line_digest, line_no, occurred_at,
                "execution.message", "within", "execution", "message",
            )
            envelope["summary"] = "kilo text part (redacted, digest only)"
            return envelope

        if native_type == "tool_use":
            part = record.get("part")
            if not isinstance(part, dict):
                return "HOOK_EVENT_INVALID:KILO_RECORD_INVALID:part"
            name = part.get("name")
            if not isinstance(name, str) or not TOOL_NAME.match(name):
                return "HOOK_EVENT_INVALID:KILO_RECORD_INVALID:tool_name"
            state = part.get("state")
            status = state.get("status") if isinstance(state, dict) else None
            if status not in STATUS_VOCABULARY:
                return f"HOOK_ADAPTER_UNAVAILABLE:KILO_STATUS_UNKNOWN:{status}"
            input_digest = sha256_hex(canonical_json(state.get("input", "")))
            if status == "running":
                if not self._emits("tool.execute.before"):
                    return "HOOK_ADAPTER_UNAVAILABLE:TYPE_NOT_EMITTED:tool.execute.before"
                envelope = self._base_envelope(
                    meta, record, line_digest, line_no, occurred_at,
                    "tool.execute.before", "before", "tool", "execute",
                )
                envelope["command_digest"] = input_digest
                envelope["summary"] = f"kilo tool {name} running (input redacted)"
                return envelope
            if not self._emits("tool.execute.after"):
                return "HOOK_ADAPTER_UNAVAILABLE:TYPE_NOT_EMITTED:tool.execute.after"
            envelope = self._base_envelope(
                meta, record, line_digest, line_no, occurred_at,
                "tool.execute.after", "after", "tool", "execute",
            )
            envelope["command_digest"] = input_digest
            if status == "failed":
                envelope["state"] = "FAILED"
                envelope["blocker_code"] = "KILO_TOOL_FAILED"
                envelope["summary"] = f"kilo tool {name} failed (input/output redacted)"
            else:
                envelope["summary"] = (
                    f"kilo tool {name} completed (input/output redacted)"
                )
            return envelope

        return f"HOOK_ADAPTER_UNAVAILABLE:KILO_TYPE_UNKNOWN:{native_type}"


def load_capability():
    return json.loads((FIXTURES / "capability.json").read_text(encoding="utf-8"))


def load_stream(name):
    base = FIXTURES / "native" / name
    meta = json.loads((base / "stream-meta.json").read_text(encoding="utf-8"))
    ndjson = (base / "stream.ndjson").read_text(encoding="utf-8")
    return meta, ndjson


def load_expected(name):
    return json.loads((FIXTURES / "normalized" / name).read_text(encoding="utf-8"))


def run_stream(name, capability=None, context=None):
    meta, ndjson = load_stream(name)
    harness = KiloHookAdapterHarness(
        capability if capability is not None else load_capability(),
        context=context,
    )
    return harness.normalize_stream(meta, ndjson)


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def test_dependency_contract_is_the_frozen_hook_contract_v1() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["$id"] == "urn:a-conductor:schema:hook-contract:1.0.0"
    contract_text = CONTRACT.read_text(encoding="utf-8")
    assert "f20fff006aad1e592b150ffdcb52ac331ec00a3a" in contract_text
    assert "fake-secret-corpus/1" in contract_text
    assert "supports_sequence" in contract_text


def test_capability_document_declares_v1_surface() -> None:
    capability = load_capability()
    assert capability["adapter_id"] == "kilo-hook-adapter"
    assert capability["adapter_version"] == "1.0.0"
    assert capability["contract_version"] == "1.0.0"
    assert capability["redaction_policy"] == "fake-secret-corpus/1"
    assert capability["supports_sequence"] is False
    assert set(capability["emits"]) == {
        "transport.adapter_capabilities",
        "execution.step_start",
        "execution.message",
        "tool.execute.before",
        "tool.execute.after",
    }


def test_session_basic_matches_expected_envelopes_exactly() -> None:
    events, reasons = run_stream("session-basic")
    expected = load_expected("expected-session-basic.json")
    assert events == expected
    assert reasons == ["HOOK_ADAPTER_UNAVAILABLE:KILO_TYPE_UNKNOWN:permission_request"]


def test_session_basic_all_envelopes_validate_against_hook_contract(
    validator,
) -> None:
    events, _ = run_stream("session-basic")
    assert events
    for envelope in events:
        assert validator.is_valid(envelope), validator.iter_errors(envelope)


def test_capability_event_is_first_and_carries_adapter_document(validator) -> None:
    events, _ = run_stream("session-basic")
    first = events[0]
    assert first["event_type"] == "transport.adapter_capabilities"
    assert first["phase"] == "before"
    assert first["adapter"] == load_capability()
    assert validator.is_valid(first)


def test_event_ids_are_unique_v4_shaped_hk_ids() -> None:
    events, _ = run_stream("session-basic")
    ids = [event["event_id"] for event in events]
    assert len(set(ids)) == len(ids)
    for event_id in ids:
        assert re.fullmatch(r"hk-[0-9a-f]{32}", event_id)
        body = event_id[3:]
        assert body[12] == "4" and body[16] in "89ab"


def test_duplicate_native_record_reuses_identity_for_dedupe() -> None:
    meta, ndjson = load_stream("session-basic")
    lines = [line for line in ndjson.splitlines() if line.strip()]
    doubled = "\n".join(lines + [lines[0]]) + "\n"
    harness = KiloHookAdapterHarness(load_capability())
    events, _ = harness.normalize_stream(meta, doubled)
    first, repeat = events[1], events[-1]
    assert first["event_id"] == repeat["event_id"]
    assert first["dedupe_key"] == repeat["dedupe_key"]
    assert first["evidence_refs"] == [f"{meta['evidence_base']}:L1"]
    assert repeat["evidence_refs"] == [f"{meta['evidence_base']}:L7"]
    assert {k for k in first if first[k] != repeat[k]} == {"evidence_refs"}


def test_no_sequence_claimed_and_arrival_order_preserved() -> None:
    events, _ = run_stream("session-basic")
    for event in events:
        assert "sequence" not in event
    assert [event["event_type"] for event in events[1:]] == [
        "execution.step_start",
        "tool.execute.before",
        "tool.execute.after",
        "tool.execute.after",
        "execution.message",
    ]
    # Native line 3 carries an earlier timestamp than line 2; observed
    # arrival order wins and the adapter never sorts by occurred_at.
    assert events[2]["occurred_at"] > events[3]["occurred_at"]


def test_redaction_stream_never_leaks_corpus_or_share_urls(validator) -> None:
    events, reasons = run_stream("session-redaction")
    expected = load_expected("expected-session-redaction.json")
    assert events == expected
    assert reasons == []
    for envelope in events:
        assert validator.is_valid(envelope)
        serialized = json.dumps(envelope, ensure_ascii=False)
        for corpus_item in FAKE_SECRET_CORPUS:
            assert corpus_item not in serialized
        assert "app.kilo.ai/s/" not in serialized
        if envelope["event_type"].startswith("tool."):
            assert "redacted" in envelope["summary"]
        if envelope["event_type"] == "execution.message":
            assert envelope["summary"] == "kilo text part (redacted, digest only)"


def test_redaction_digests_are_verifiable_against_native_records() -> None:
    meta, ndjson = load_stream("session-redaction")
    events, _ = run_stream("session-redaction")
    native_by_line = {}
    for line_no, line in enumerate(ndjson.splitlines(), start=1):
        if line.strip():
            native_by_line[line_no] = line.strip()
    tool_events = [event for event in events if event["event_type"].startswith("tool.")]
    assert tool_events
    for event in tool_events:
        line_no = int(event["evidence_refs"][0].rsplit(":L", 1)[1])
        record = json.loads(native_by_line[line_no])
        state = record["part"]["state"]
        assert event["command_digest"] == sha256_hex(canonical_json(state.get("input", "")))
        assert event["evidence_digest"] == sha256_hex(native_by_line[line_no])
    message_events = [event for event in events if event["event_type"] == "execution.message"]
    assert len(message_events) == 1
    message_line_no = int(message_events[0]["evidence_refs"][0].rsplit(":L", 1)[1])
    assert message_events[0]["evidence_digest"] == sha256_hex(native_by_line[message_line_no])
    assert message_events[0].get("summary") == "kilo text part (redacted, digest only)"
    assert "part" not in message_events[0]


def test_unknown_native_type_is_dropped_never_invented() -> None:
    events, reasons = run_stream("session-basic")
    assert "permission_request" not in json.dumps(events)
    assert any("KILO_TYPE_UNKNOWN:permission_request" in reason for reason in reasons)
    assert not any(event["event_type"].startswith("permission") for event in events)


def test_provider_model_mismatch_fails_closed_without_fallback() -> None:
    events, reasons = run_stream("provider-mismatch")
    assert events == []
    assert any("KILO_PROVIDER_MODEL_MISMATCH" in reason for reason in reasons)
    assert any(reason.startswith("HOOK_ADAPTER_UNAVAILABLE") for reason in reasons)


def test_mapping_is_provider_model_independent_metadata_only() -> None:
    meta, ndjson = load_stream("session-basic")
    events_a, _ = KiloHookAdapterHarness(load_capability()).normalize_stream(
        dict(meta), ndjson
    )
    meta_b = dict(meta, provider_model="other-vendor/other-model")
    context_b = dict(CONTEXT, expected_provider_model="other-vendor/other-model")
    events_b, _ = KiloHookAdapterHarness(load_capability(), context=context_b).normalize_stream(
        meta_b, ndjson
    )
    assert len(events_a) == len(events_b)
    # The capability event carries no model metadata; it must be identical.
    assert events_a[0] == events_b[0]
    for event_a, event_b in zip(events_a[1:], events_b[1:]):
        diff = {
            key for key in set(event_a) | set(event_b) if event_a.get(key) != event_b.get(key)
        }
        assert diff == {"model_id"}, diff


@pytest.mark.parametrize("stream_name", ["version-drift", "version-unverified"])
def test_version_drift_fails_closed(stream_name) -> None:
    events, reasons = run_stream(stream_name)
    assert events == []
    assert any(reason.startswith("HOOK_VERSION_UNSUPPORTED") for reason in reasons)
    assert any("KILO_VERSION_UNSUPPORTED" in reason for reason in reasons)


def test_same_minor_family_version_maps() -> None:
    meta, ndjson = load_stream("session-basic")
    meta = dict(meta, kilo_version="7.7.9")
    events, reasons = KiloHookAdapterHarness(load_capability()).normalize_stream(meta, ndjson)
    assert reasons == [
        "HOOK_ADAPTER_UNAVAILABLE:KILO_TYPE_UNKNOWN:permission_request"
    ]
    assert all(event["source_version"] == "7.7.9" for event in events[1:])


def test_missing_capability_document_fails_closed() -> None:
    meta, ndjson = load_stream("session-basic")
    harness = KiloHookAdapterHarness(capability=None)
    events, reasons = harness.normalize_stream(meta, ndjson)
    assert events == []
    assert reasons == ["HOOK_ADAPTER_UNAVAILABLE:missing_capability_document"]


def test_capability_contract_version_gate_fails_closed() -> None:
    capability = load_capability()
    capability["contract_version"] = "2.0.0"
    events, reasons = run_stream("session-basic", capability=capability)
    assert events == []
    assert any(reason.startswith("HOOK_VERSION_UNSUPPORTED") for reason in reasons)


def test_emits_list_scopes_emission() -> None:
    capability = load_capability()
    capability["emits"] = [
        event_type
        for event_type in capability["emits"]
        if event_type != "execution.message"
    ]
    events, reasons = run_stream("session-basic", capability=capability)
    assert all(event["event_type"] != "execution.message" for event in events)
    assert any("TYPE_NOT_EMITTED:execution.message" in reason for reason in reasons)
    assert any(event["event_type"] == "execution.step_start" for event in events)


def test_invalid_records_typed_and_offset_timestamp_converted() -> None:
    events, reasons = run_stream("invalid-records")
    assert len(events) == 2
    mapped = events[1]
    assert mapped["event_type"] == "tool.execute.before"
    assert mapped["occurred_at"] == "2026-09-19T08:41:05.500Z"
    assert sum("KILO_RECORD_INVALID" in reason for reason in reasons) == 3
    assert any("KILO_STATUS_UNKNOWN:escalated" in reason for reason in reasons)


def test_envelopes_respect_size_and_forbidden_field_rules(validator) -> None:
    for stream_name in ("session-basic", "session-redaction", "invalid-records"):
        events, _ = run_stream(stream_name)
        for envelope in events:
            serialized = json.dumps(envelope, ensure_ascii=False)
            assert len(serialized.encode("utf-8")) <= MAX_ENVELOPE_BYTES
            for field_name in FORBIDDEN_FIELDS:
                assert field_name not in envelope
            summary = envelope.get("summary")
            if summary is not None:
                assert 1 <= len(summary) <= 512
            assert envelope["privacy_class"] != "SECRET"
            assert validator.is_valid(envelope)
