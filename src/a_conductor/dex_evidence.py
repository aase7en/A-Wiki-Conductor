"""Strict DEX collection-evidence decoder."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any

_SCHEMA = "dex.srm.collection.v1"
_MAX_BYTES = 262144
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_TOP = frozenset(("schema","execution_id","attempt_id","binding_digest","claim_generation","sha_set","process","artifacts","result","collected_under_drift","evidence_sha256"))


class DexEvidenceError(RuntimeError):
    quarantine_required = True

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class _DuplicateKey(ValueError):
    pass


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise _DuplicateKey(key)
        out[key] = value
    return out


def _constant(value: str) -> None:
    raise ValueError(value)


def _text(value: Any, code: str, maximum: int = 1024) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum or any(c in value for c in ("\x00", "\r", "\n")):
        raise DexEvidenceError(code)
    return value


def _hex(value: Any, pattern: re.Pattern[str], code: str) -> str:
    value = _text(value, code, pattern.pattern.count("0") + 128)
    if pattern.fullmatch(value) is None:
        raise DexEvidenceError(code)
    return value


def _uint(value: Any, code: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise DexEvidenceError(code)
    return value


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",",":"), ensure_ascii=True).encode("utf-8")


@dataclass(frozen=True, slots=True)
class DexArtifactDigest:
    ref: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class DexCollectedEvidence:
    execution_id: str
    attempt_id: str
    binding_digest: str
    claim_generation: int
    authority_sha: str
    execution_sha: str
    host_id: str
    boot_id: str
    pid: int
    creation_id: str
    exit_code: int
    artifacts: tuple[DexArtifactDigest, ...]
    result_ref: str
    result_sha256: str
    collected_under_drift: bool
    evidence_sha256: str


def decode_collected_evidence(raw: bytes, *, expected_execution_id: str, expected_attempt_id: str, expected_binding_digest: str, expected_authority_sha: str, expected_execution_sha: str) -> DexCollectedEvidence:
    if not isinstance(raw, bytes) or not raw or len(raw) > _MAX_BYTES:
        raise DexEvidenceError("DEX_EVIDENCE_BYTES_INVALID")
    try:
        payload = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_object, parse_constant=_constant)
    except _DuplicateKey as exc:
        raise DexEvidenceError("DEX_EVIDENCE_DUPLICATE_KEY") from exc
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise DexEvidenceError("DEX_EVIDENCE_JSON_INVALID") from exc
    if not isinstance(payload, dict):
        raise DexEvidenceError("DEX_EVIDENCE_ROOT_INVALID")
    if set(payload) != _TOP:
        raise DexEvidenceError("DEX_EVIDENCE_KEYS_INVALID")
    if payload["schema"] != _SCHEMA:
        raise DexEvidenceError("DEX_EVIDENCE_SCHEMA_MISMATCH")

    execution_id = _text(payload["execution_id"], "DEX_EVIDENCE_EXECUTION_INVALID")
    attempt_id = _text(payload["attempt_id"], "DEX_EVIDENCE_ATTEMPT_INVALID")
    binding = _hex(payload["binding_digest"], _HEX64, "DEX_EVIDENCE_BINDING_INVALID")
    generation = _uint(payload["claim_generation"], "DEX_EVIDENCE_GENERATION_INVALID")

    sha_set = payload["sha_set"]
    if not isinstance(sha_set, dict) or set(sha_set) != {"authority","execution"}:
        raise DexEvidenceError("DEX_EVIDENCE_SHA_SET_INVALID")
    authority_sha = _hex(sha_set["authority"], _HEX40, "DEX_EVIDENCE_SHA_SET_INVALID")
    execution_sha = _hex(sha_set["execution"], _HEX40, "DEX_EVIDENCE_SHA_SET_INVALID")

    process = payload["process"]
    if not isinstance(process, dict) or set(process) != {"host_id","boot_id","pid","creation_id","exit_code"}:
        raise DexEvidenceError("DEX_EVIDENCE_PROCESS_INVALID")
    host_id = _text(process["host_id"], "DEX_EVIDENCE_PROCESS_INVALID")
    boot_id = _text(process["boot_id"], "DEX_EVIDENCE_PROCESS_INVALID")
    pid = _uint(process["pid"], "DEX_EVIDENCE_PROCESS_INVALID")
    creation_id = _text(process["creation_id"], "DEX_EVIDENCE_PROCESS_INVALID")
    exit_code = process["exit_code"]
    if pid < 1 or not isinstance(exit_code, int) or isinstance(exit_code, bool):
        raise DexEvidenceError("DEX_EVIDENCE_PROCESS_INVALID")

    artifacts_raw = payload["artifacts"]
    if not isinstance(artifacts_raw, list) or not artifacts_raw or len(artifacts_raw) > 16:
        raise DexEvidenceError("DEX_EVIDENCE_ARTIFACTS_INVALID")
    artifacts: list[DexArtifactDigest] = []
    refs: set[str] = set()
    for item in artifacts_raw:
        if not isinstance(item, dict) or set(item) != {"ref","sha256","size_bytes"}:
            raise DexEvidenceError("DEX_EVIDENCE_ARTIFACTS_INVALID")
        ref = _text(item["ref"], "DEX_EVIDENCE_ARTIFACTS_INVALID")
        if ref in refs:
            raise DexEvidenceError("DEX_EVIDENCE_ARTIFACTS_INVALID")
        refs.add(ref)
        artifacts.append(DexArtifactDigest(ref, _hex(item["sha256"], _HEX64, "DEX_EVIDENCE_ARTIFACTS_INVALID"), _uint(item["size_bytes"], "DEX_EVIDENCE_ARTIFACTS_INVALID")))

    result = payload["result"]
    if not isinstance(result, dict) or set(result) != {"ref","sha256"}:
        raise DexEvidenceError("DEX_EVIDENCE_RESULT_INVALID")
    result_ref = _text(result["ref"], "DEX_EVIDENCE_RESULT_INVALID")
    result_sha = _hex(result["sha256"], _HEX64, "DEX_EVIDENCE_RESULT_INVALID")
    if {item.ref:item.sha256 for item in artifacts}.get(result_ref) != result_sha:
        raise DexEvidenceError("DEX_EVIDENCE_RESULT_DIGEST_MISMATCH")

    drift = payload["collected_under_drift"]
    evidence_sha = _hex(payload["evidence_sha256"], _HEX64, "DEX_EVIDENCE_DIGEST_INVALID")
    if not isinstance(drift, bool):
        raise DexEvidenceError("DEX_EVIDENCE_DRIFT_INVALID")
    if execution_id != expected_execution_id or attempt_id != expected_attempt_id:
        raise DexEvidenceError("DEX_EVIDENCE_IDENTITY_MISMATCH")
    if binding != expected_binding_digest:
        raise DexEvidenceError("DEX_EVIDENCE_BINDING_MISMATCH")
    if authority_sha != expected_authority_sha or execution_sha != expected_execution_sha:
        raise DexEvidenceError("DEX_EVIDENCE_SHA_SET_MISMATCH")

    body = dict(payload)
    del body["evidence_sha256"]
    if hashlib.sha256(_canonical(body)).hexdigest() != evidence_sha:
        raise DexEvidenceError("DEX_EVIDENCE_DIGEST_MISMATCH")
    return DexCollectedEvidence(execution_id, attempt_id, binding, generation, authority_sha, execution_sha, host_id, boot_id, pid, creation_id, exit_code, tuple(artifacts), result_ref, result_sha, drift, evidence_sha)
