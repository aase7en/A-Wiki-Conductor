from __future__ import annotations

import json

import pytest

from a_conductor.dex_evidence import DexEvidenceError, decode_collected_evidence
from a_conductor.dex_fake_substrate import FakeSrmCollectionProducer


BINDING = "d" * 64
AUTH_SHA = "a" * 40
EXEC_SHA = "b" * 40


def _producer() -> FakeSrmCollectionProducer:
    return FakeSrmCollectionProducer(
        execution_id="exec-001",
        attempt_id="attempt-001",
        binding_digest=BINDING,
        claim_generation=4,
        authority_sha=AUTH_SHA,
        execution_sha=EXEC_SHA,
        host_id="host-01",
        boot_id="boot-01",
        pid=4321,
        creation_id="proc-created-01",
    )


def _raw() -> bytes:
    return _producer().collect(
        result_bytes=b'{"status":"ok"}',
        stdout_bytes=b"hello\n",
        stderr_bytes=b"",
        exit_code=0,
    )


def _decode(raw: bytes):
    return decode_collected_evidence(
        raw,
        expected_execution_id="exec-001",
        expected_attempt_id="attempt-001",
        expected_binding_digest=BINDING,
        expected_authority_sha=AUTH_SHA,
        expected_execution_sha=EXEC_SHA,
    )


def test_valid_collection_decodes_and_binds_all_identity() -> None:
    evidence = _decode(_raw())
    assert evidence.execution_id == "exec-001"
    assert evidence.attempt_id == "attempt-001"
    assert evidence.binding_digest == BINDING
    assert evidence.claim_generation == 4
    assert evidence.authority_sha == AUTH_SHA
    assert evidence.execution_sha == EXEC_SHA
    assert evidence.result_sha256 in {item.sha256 for item in evidence.artifacts}


def test_duplicate_json_key_is_rejected_before_projection() -> None:
    raw = b'{"schema":"dex.srm.collection.v1","schema":"dex.srm.collection.v1"}'
    with pytest.raises(DexEvidenceError, match="DEX_EVIDENCE_DUPLICATE_KEY"):
        _decode(raw)


def test_unknown_top_level_field_is_rejected() -> None:
    payload = json.loads(_raw())
    payload["receipt"] = {"accepted": True}
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    with pytest.raises(DexEvidenceError, match="DEX_EVIDENCE_KEYS_INVALID"):
        _decode(raw)


def test_expected_binding_and_sha_set_mismatch_fail_closed() -> None:
    raw = _raw()
    with pytest.raises(DexEvidenceError, match="DEX_EVIDENCE_BINDING_MISMATCH"):
        decode_collected_evidence(
            raw,
            expected_execution_id="exec-001",
            expected_attempt_id="attempt-001",
            expected_binding_digest="e" * 64,
            expected_authority_sha=AUTH_SHA,
            expected_execution_sha=EXEC_SHA,
        )
    with pytest.raises(DexEvidenceError, match="DEX_EVIDENCE_SHA_SET_MISMATCH"):
        decode_collected_evidence(
            raw,
            expected_execution_id="exec-001",
            expected_attempt_id="attempt-001",
            expected_binding_digest=BINDING,
            expected_authority_sha="f" * 40,
            expected_execution_sha=EXEC_SHA,
        )


def test_result_digest_chain_mismatch_is_rejected() -> None:
    payload = json.loads(_raw())
    payload["result"]["sha256"] = "0" * 64
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    with pytest.raises(DexEvidenceError, match="DEX_EVIDENCE_RESULT_DIGEST_MISMATCH"):
        _decode(raw)


def test_evidence_digest_tamper_is_rejected() -> None:
    payload = json.loads(_raw())
    payload["process"]["exit_code"] = 9
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    with pytest.raises(DexEvidenceError, match="DEX_EVIDENCE_DIGEST_MISMATCH"):
        _decode(raw)


def _retag(payload: dict) -> bytes:
    import hashlib

    body = dict(payload)
    body.pop("evidence_sha256", None)
    canonical = json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    payload["evidence_sha256"] = hashlib.sha256(canonical).hexdigest()
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


@pytest.mark.parametrize("bad_id", ["exec\nsmuggled", "exec\x00smuggled"])
def test_identity_control_characters_are_rejected(bad_id: str) -> None:
    payload = json.loads(_raw())
    payload["execution_id"] = bad_id
    raw = _retag(payload)
    with pytest.raises(DexEvidenceError, match="DEX_EVIDENCE_EXECUTION_INVALID"):
        decode_collected_evidence(
            raw,
            expected_execution_id=bad_id,
            expected_attempt_id="attempt-001",
            expected_binding_digest=BINDING,
            expected_authority_sha=AUTH_SHA,
            expected_execution_sha=EXEC_SHA,
        )


def test_duplicate_artifact_ref_is_rejected() -> None:
    payload = json.loads(_raw())
    payload["artifacts"][1]["ref"] = "result"
    raw = _retag(payload)
    with pytest.raises(DexEvidenceError, match="DEX_EVIDENCE_ARTIFACTS_INVALID"):
        _decode(raw)


def test_nonstandard_json_constant_is_rejected() -> None:
    raw = _raw().replace(b'"exit_code":0', b'"exit_code":NaN')
    with pytest.raises(DexEvidenceError, match="DEX_EVIDENCE_JSON_INVALID"):
        _decode(raw)
