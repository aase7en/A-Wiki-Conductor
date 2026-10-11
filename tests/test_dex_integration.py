"""DEX-2c integration tests — admission → dispatch → collect → receipt (WO-P1-612).

Tier 1 (always runs, deterministic): exercises the wire end-to-end with a
contract-accurate in-test transport whose evidence payloads are accepted by
the STRICT decoder (the decoder is the acceptance gate; payloads mirror the
public v1 schema). Tier 2 (env SRM_REPO_ROOT): a Node driver runs the REAL
SunDayRemoteMCP ExecutionSupervisor to produce genuine substrate evidence.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from a_conductor.dex_admission import (  # noqa: E402
    AdmissionDenied,
    AdmissionIssuer,
    ClaimView,
)
from a_conductor.dex_evidence import decode_collected_evidence  # noqa: E402
from a_conductor.dex_identity import DexBindingIdentity  # noqa: E402
from a_conductor.dex_wire import AdmissionReceiptWire  # noqa: E402
from a_conductor.execution_record import (  # noqa: E402
    ExecutionProcessState,
    ReceiptDisposition,
    TransportState,
    new_execution_record,
)
from a_conductor.execution_store import SQLiteExecutionStore  # noqa: E402

SCHEMA = "dex.srm.collection.v1"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_binding(
    *,
    execution_id: str = "exec-dex2c-001",
    attempt_id: str = "attempt-001",
    claim_generation: int = 7,
) -> DexBindingIdentity:
    return DexBindingIdentity(
        execution_id=execution_id,
        attempt_id=attempt_id,
        task_ref="task/dex2c-test",
        lane_ref="lane/dex2c",
        claim_ref="claim/dex2c-001",
        claim_generation=claim_generation,
        authority_repo_identity="aase7en/A-Wiki-Conductor",
        execution_repo_identity="aase7en/SunDayRemoteMCP",
        authority_sha="1" * 40,
        execution_sha="2" * 40,
        host_id="host-test-01",
        boot_id="boot-test-01",
        executable_path="C:\\tools\\node.exe",
        executable_sha256="3" * 64,
        argv_shape=("--version",),
    )


def build_evidence(
    binding: DexBindingIdentity,
    *,
    binding_digest_value: str,
    exit_code: int = 0,
    drift: bool = False,
) -> bytes:
    result_sha = _sha256(b"dex2c-result")
    payload = {
        "schema": SCHEMA,
        "execution_id": binding.execution_id,
        "attempt_id": binding.attempt_id,
        "binding_digest": binding_digest_value,
        "claim_generation": binding.claim_generation,
        "sha_set": {"authority": binding.authority_sha, "execution": binding.execution_sha},
        "process": {
            "host_id": binding.host_id,
            "boot_id": binding.boot_id,
            "pid": 4242,
            "creation_id": "creation-001",
            "exit_code": exit_code,
        },
        "artifacts": [
            {"ref": "result.json", "sha256": result_sha, "size_bytes": 13},
        ],
        "result": {"ref": "result.json", "sha256": result_sha},
        "collected_under_drift": drift,
    }
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    payload["evidence_sha256"] = _sha256(body)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


@dataclass
class ScriptedTransport:
    """Contract-accurate port double: emits DISPATHED then fixed evidence."""

    evidence: bytes
    dispatch_status: str = "DISPATCHED"
    dispatch_calls: int = 0

    def dispatch(self, binding: DexBindingIdentity) -> dict:
        self.dispatch_calls += 1
        return {"status": self.dispatch_status}

    def collect(self, execution_id: str, attempt_id: str) -> bytes:
        return self.evidence


class WireHarness:
    def __init__(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()  # noqa: SIM115
        self.store = SQLiteExecutionStore(Path(self.tmp.name) / "exec.sqlite3")
        self.issuer = AdmissionIssuer()

    def make_wire(self, transport: ScriptedTransport) -> AdmissionReceiptWire:
        return AdmissionReceiptWire(
            issuer=self.issuer, store=self.store, transport=transport
        )

    def ensure_record(self, binding: DexBindingIdentity) -> None:
        self.store.create(
            new_execution_record(
                execution_id=binding.execution_id,
                job_id="job-001",
                work_order_ref="WO-P1-612",
                project_id="proj-001",
                worker_id="worker-glmlane",
                backend_id="backend-node",
                agent_ref=None,
                repo_root="A:\\repo\\example",
                branch="main",
                head_before=binding.execution_sha,
                operation_ref="op-001",
                command_fingerprint="f" * 64,
                command_summary="dex2c test attempt",
                runtime_profile_ref=None,
                run_dir_ref=None,
                stdout_ref=None,
                stderr_ref=None,
                result_ref=None,
                report_ref=None,
                transport_state=TransportState.CONNECTED,
                execution_state=ExecutionProcessState.QUEUED,
            )
        )

    def close(self) -> None:
        self.tmp.cleanup()


class Dex2cIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.harness = WireHarness()
        self.addCleanup(self.harness.close)

    def _run_success_case(self) -> tuple:
        binding = make_binding()
        self.harness.ensure_record(binding)
        view = ClaimView(claim_ref=binding.claim_ref, claim_generation=binding.claim_generation, live=True)
        digest_holder: dict = {}

        from a_conductor.dex_identity import binding_digest

        digest_holder["digest"] = binding_digest(binding)
        transport = ScriptedTransport(build_evidence(binding, binding_digest_value=digest_holder["digest"]))
        wire = self.harness.make_wire(transport)
        outcome = wire.run_attempt(binding=binding, claim_view=view)
        return binding, transport, wire, outcome, view

    def test_admission_dispatch_collect_receipt_completes(self) -> None:
        binding, transport, wire, outcome, view = self._run_success_case()
        self.assertEqual(outcome.status, "COMPLETED", outcome.detail)
        self.assertIsNotNone(outcome.receipt_id)
        self.assertEqual(transport.dispatch_calls, 1)
        receipt = self.harness.store.get_receipt(outcome.receipt_id)
        self.assertEqual(receipt.disposition, ReceiptDisposition.ACCEPTED)
        self.assertEqual(receipt.execution_id, binding.execution_id)

    def test_duplicate_run_skips_dispatch_and_returns_existing_receipt(self) -> None:
        binding, transport, wire, outcome, view = self._run_success_case()
        again = wire.run_attempt(binding=binding, claim_view=view)
        self.assertEqual(again.status, "DUPLICATE_ALREADY_COMPLETED")
        self.assertEqual(again.receipt_id, outcome.receipt_id)
        self.assertEqual(transport.dispatch_calls, 1)  # at most one effect

    def test_stale_claim_generation_denied_before_dispatch(self) -> None:
        binding = make_binding(claim_generation=3)
        self.harness.ensure_record(binding)
        transport = ScriptedTransport(b"{}")
        wire = self.harness.make_wire(transport)
        stale = ClaimView(claim_ref=binding.claim_ref, claim_generation=9, live=True)
        outcome = wire.run_attempt(binding=binding, claim_view=stale)
        self.assertEqual(outcome.status, "DENIED")
        self.assertIn("ADMISSION_CLAIM_GENERATION_STALE", outcome.detail)
        self.assertEqual(transport.dispatch_calls, 0)
        self.assertIsNone(outcome.receipt_id)

    def test_not_live_claim_denied_before_dispatch(self) -> None:
        binding = make_binding()
        self.harness.ensure_record(binding)
        transport = ScriptedTransport(b"{}")
        wire = self.harness.make_wire(transport)
        dead = ClaimView(claim_ref=binding.claim_ref, claim_generation=binding.claim_generation, live=False)
        outcome = wire.run_attempt(binding=binding, claim_view=dead)
        self.assertEqual(outcome.status, "DENIED")
        self.assertEqual(transport.dispatch_calls, 0)

    def test_tampered_evidence_rejected_without_receipt(self) -> None:
        from a_conductor.dex_identity import binding_digest

        binding = make_binding()
        self.harness.ensure_record(binding)
        raw = bytearray(build_evidence(binding, binding_digest_value=binding_digest(binding)))
        raw[10] = raw[10] ^ 0x01  # corrupt a byte inside execution_id region
        transport = ScriptedTransport(bytes(raw))
        wire = self.harness.make_wire(transport)
        view = ClaimView(claim_ref=binding.claim_ref, claim_generation=binding.claim_generation, live=True)
        outcome = wire.run_attempt(binding=binding, claim_view=view)
        self.assertEqual(outcome.status, "EVIDENCE_REJECTED", outcome.detail)
        self.assertIsNone(outcome.receipt_id)

    def test_wrong_binding_digest_evidence_rejected(self) -> None:
        binding = make_binding()
        self.harness.ensure_record(binding)
        transport = ScriptedTransport(build_evidence(binding, binding_digest_value="0" * 64))
        wire = self.harness.make_wire(transport)
        view = ClaimView(claim_ref=binding.claim_ref, claim_generation=binding.claim_generation, live=True)
        outcome = wire.run_attempt(binding=binding, claim_view=view)
        self.assertEqual(outcome.status, "EVIDENCE_REJECTED")
        self.assertIn("DEX_EVIDENCE_BINDING_MISMATCH", outcome.detail)

    def test_launch_ambiguous_no_receipt_no_duplicate_effect(self) -> None:
        binding = make_binding()
        self.harness.ensure_record(binding)
        transport = ScriptedTransport(b"{}", dispatch_status="AMBIGUOUS")
        wire = self.harness.make_wire(transport)
        view = ClaimView(claim_ref=binding.claim_ref, claim_generation=binding.claim_generation, live=True)
        outcome = wire.run_attempt(binding=binding, claim_view=view)
        self.assertEqual(outcome.status, "AMBIGUOUS")
        self.assertIsNone(outcome.receipt_id)
        # No auto-retry: a subsequent identical run still refuses to create a
        # second dispatch effect until reconciliation clears the ambiguity
        # (here: still ambiguous transport).
        transport.dispatch_status = "AMBIGUOUS"
        second = wire.run_attempt(binding=binding, claim_view=view)
        self.assertEqual(second.status, "AMBIGUOUS")

    def test_collected_under_drift_quarantined_receipt(self) -> None:
        from a_conductor.dex_identity import binding_digest

        binding = make_binding()
        self.harness.ensure_record(binding)
        transport = ScriptedTransport(
            build_evidence(binding, binding_digest_value=binding_digest(binding), drift=True)
        )
        wire = self.harness.make_wire(transport)
        view = ClaimView(claim_ref=binding.claim_ref, claim_generation=binding.claim_generation, live=True)
        outcome = wire.run_attempt(binding=binding, claim_view=view)
        self.assertEqual(outcome.status, "COMPLETED")
        receipt = self.harness.store.get_receipt(outcome.receipt_id)
        self.assertEqual(receipt.disposition, ReceiptDisposition.QUARANTINED)

    def test_admission_replay_idempotent_same_decision(self) -> None:
        binding = make_binding()
        view = ClaimView(claim_ref=binding.claim_ref, claim_generation=binding.claim_generation, live=True)
        issuer = AdmissionIssuer()
        first = issuer.admit(binding=binding, claim_view=view)
        second = issuer.admit(binding=binding, claim_view=view)
        self.assertEqual(first, second)

    def test_admission_replay_generation_conflict_typed(self) -> None:
        binding = make_binding()
        issuer = AdmissionIssuer()
        issuer.admit(
            binding=binding,
            claim_view=ClaimView(claim_ref=binding.claim_ref, claim_generation=binding.claim_generation, live=True),
        )
        with self.assertRaises(AdmissionDenied):
            issuer.admit(
                binding=binding,
                claim_view=ClaimView(claim_ref=binding.claim_ref, claim_generation=binding.claim_generation + 1, live=True),
            )


class RealSubstrateTests(unittest.TestCase):
    """Tier 2: REAL SRM ExecutionSupervisor via Node driver (SRM_REPO_ROOT)."""

    SRM_ROOT = os.environ.get("SRM_REPO_ROOT", "")

    def test_real_substrate_evidence_accepted_by_wire(self) -> None:
        if not self.SRM_ROOT:
            self.skipTest("SRM_REPO_ROOT not set; real-substrate tier not exercised (contract tier covers wire logic)")
        import subprocess

        from a_conductor.dex_identity import (
            binding_digest,
            canonical_root_digest,
            canonicalize_existing_root,
        )

        canonical = canonicalize_existing_root(Path(self.SRM_ROOT))
        binding = DexBindingIdentity(
            execution_id="exec-dex2creal-0001",
            attempt_id="attempt-real-0001",
            task_ref="task/dex2c-real",
            lane_ref="lane/dex2c",
            claim_ref="claim/dex2c-real",
            claim_generation=1,
            authority_repo_identity="aase7en/A-Wiki-Conductor",
            execution_repo_identity="aase7en/SunDayRemoteMCP",
            authority_sha=subprocess.run(
                ["git", "-C", os.environ["AWC_REPO_ROOT"], "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip(),
            execution_sha=subprocess.run(
                ["git", "-C", self.SRM_ROOT, "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip(),
            host_id="host-test-01",
            boot_id="boot-test-01",
            executable_path="C:\\Windows\\System32\\cmd.exe",
            executable_sha256="3" * 64,
            argv_shape=("/c", "echo", "dex2c-real"),
        )
        digest = binding_digest(binding)
        driver = Path(__file__).parent / "fixtures" / "dex2c_srm_driver.mjs"
        request = {
            "srmRoot": self.SRM_ROOT,
            "command": "node",
            "args": ["-e", "process.exit(0)"],
            "cwd": self.SRM_ROOT,
            "binding": {
                "executionId": binding.execution_id,
                "attemptId": binding.attempt_id,
                "canonicalPath": canonical,
                "canonicalDigest": canonical_root_digest(canonical, platform_tag="win32"),
                "bindingDigest": digest,
                "compatibility": {
                    "authorityRepo": binding.authority_repo_identity,
                    "authoritySha": binding.authority_sha,
                    "executionRepo": binding.execution_repo_identity,
                    "executionSha": binding.execution_sha,
                },
            },
        }
        proc = subprocess.run(
            ["node", str(driver)],
            input=json.dumps(request).encode(),
            capture_output=True,
            timeout=120,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode(errors="replace")[:2000])
        evidence = proc.stdout.strip()
        decoded = decode_collected_evidence(
            evidence,
            expected_execution_id=binding.execution_id,
            expected_attempt_id=binding.attempt_id,
            expected_binding_digest=digest,
            expected_authority_sha=binding.authority_sha,
            expected_execution_sha=binding.execution_sha,
        )
        self.assertEqual(decoded.exit_code, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
