"""Contract-shaped fake SRM collection producer for deterministic DEX tests.

The fake emits immutable substrate-observed evidence only. It intentionally
contains no receipt, retry, review, task-completion, or acceptance decision.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

_MAX_ARTIFACT_BYTES = 1024 * 1024
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_HEX40 = re.compile(r"^[0-9a-f]{40}$")


class FakeSrmCollectionError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 1024:
        raise ValueError(f"{field} is invalid")
    if "\x00" in value or "\r" in value or "\n" in value:
        raise ValueError(f"{field} is invalid")
    return value


def _canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",",":"), ensure_ascii=True).encode("utf-8")


class FakeSrmCollectionProducer:
    """One-attempt immutable substrate evidence fixture."""

    def __init__(
        self,
        *,
        execution_id: str,
        attempt_id: str,
        binding_digest: str,
        claim_generation: int,
        authority_sha: str,
        execution_sha: str,
        host_id: str,
        boot_id: str,
        pid: int,
        creation_id: str,
    ) -> None:
        self.execution_id = _text(execution_id, "execution_id")
        self.attempt_id = _text(attempt_id, "attempt_id")
        if not isinstance(binding_digest, str) or _HEX64.fullmatch(binding_digest) is None:
            raise ValueError("binding_digest is invalid")
        if not isinstance(claim_generation, int) or isinstance(claim_generation, bool) or claim_generation < 0:
            raise ValueError("claim_generation is invalid")
        if not isinstance(authority_sha, str) or _HEX40.fullmatch(authority_sha) is None:
            raise ValueError("authority_sha is invalid")
        if not isinstance(execution_sha, str) or _HEX40.fullmatch(execution_sha) is None:
            raise ValueError("execution_sha is invalid")
        if not isinstance(pid, int) or isinstance(pid, bool) or pid < 1:
            raise ValueError("pid is invalid")
        self.binding_digest = binding_digest
        self.claim_generation = claim_generation
        self.authority_sha = authority_sha
        self.execution_sha = execution_sha
        self.host_id = _text(host_id, "host_id")
        self.boot_id = _text(boot_id, "boot_id")
        self.pid = pid
        self.creation_id = _text(creation_id, "creation_id")
        self._signature: tuple[Any, ...] | None = None
        self._raw: bytes | None = None

    @staticmethod
    def _artifact(ref: str, data: bytes) -> dict[str, Any]:
        if not isinstance(data, bytes):
            raise FakeSrmCollectionError("FAKE_COLLECTION_ARTIFACT_INVALID")
        if len(data) > _MAX_ARTIFACT_BYTES:
            raise FakeSrmCollectionError("FAKE_COLLECTION_ARTIFACT_TOO_LARGE")
        return {"ref": ref, "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}

    def collect(
        self,
        *,
        result_bytes: bytes,
        stdout_bytes: bytes,
        stderr_bytes: bytes,
        exit_code: int,
    ) -> bytes:
        if not isinstance(exit_code, int) or isinstance(exit_code, bool):
            raise FakeSrmCollectionError("FAKE_COLLECTION_EXIT_CODE_INVALID")
        result = self._artifact("result", result_bytes)
        stdout = self._artifact("stdout", stdout_bytes)
        stderr = self._artifact("stderr", stderr_bytes)
        signature = (
            result["sha256"], result["size_bytes"],
            stdout["sha256"], stdout["size_bytes"],
            stderr["sha256"], stderr["size_bytes"],
            exit_code,
        )
        if self._signature is not None:
            if signature != self._signature:
                raise FakeSrmCollectionError("FAKE_COLLECTION_IMMUTABLE")
            assert self._raw is not None
            return self._raw

        payload: dict[str, Any] = {
            "schema": "dex.srm.collection.v1",
            "execution_id": self.execution_id,
            "attempt_id": self.attempt_id,
            "binding_digest": self.binding_digest,
            "claim_generation": self.claim_generation,
            "sha_set": {"authority": self.authority_sha, "execution": self.execution_sha},
            "process": {
                "host_id": self.host_id,
                "boot_id": self.boot_id,
                "pid": self.pid,
                "creation_id": self.creation_id,
                "exit_code": exit_code,
            },
            "artifacts": [result, stdout, stderr],
            "result": {"ref": "result", "sha256": result["sha256"]},
            "collected_under_drift": False,
        }
        payload["evidence_sha256"] = hashlib.sha256(_canonical(payload)).hexdigest()
        self._signature = signature
        self._raw = _canonical(payload)
        return self._raw
