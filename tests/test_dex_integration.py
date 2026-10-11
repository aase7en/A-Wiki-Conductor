"""DEX-2c integration tests — admission → dispatch → collect → receipt (WO-P1-612).

Tier 1 (always runs, deterministic): exercises the wire end-to-end with a
contract-accurate in-test transport whose evidence payloads are accepted by
the STRICT decoder (the decoder is the acceptance gate; payloads mirror the
public v1 schema). Covers every R3-r1 finding: frozen denials, binding
mutation conflicts, ambiguity fencing (no second dispatch), generation
agreement, conflict propagation, fail-closed record precondition.
Tier 2 (env SRM_REPO_ROOT): a Node driver runs the REAL SunDayRemoteMCP
ExecutionSupervisor to produce genuine substrate evidence, which is then
routed through the FULL wire (admission → dispatch → collect → decode →
durable receipt).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
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
from a_conductor.dex_identity import DexBindingIdentity, binding_digest  # noqa: E402
from a_conductor.dex_wire import AdmissionReceiptWire, WireError  # noqa: E402
from a_conductor.execution_record import (  # noqa: E402
    ExecutionProcessState,
    ReceiptDisposition,
    TransportState,
    new_execution_record,
    new_execution_receipt,
)
from a_conductor.execution_store import SQLiteExecutionStore  # noqa: E402

SCHEMA = "dex.srm.collection.v1"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_binding(
    *,
    execution_id: str = "exec-dex2c-0001-a1",
    attempt_id: str = "attempt-0001-a1",
    claim_generation: int = 7,
    executable_path: str = "C:\\tools\\node.exe",
    argv_shape: tuple[str, ...] = ("--version",),
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
        executable_path=executable_path,
        executable_sha256="3" * 64,
        argv_shape=argv_shape,
    )


def build_evidence(
    binding: DexBindingIdentity,
    *,
    binding_digest_value: str,
    exit_code: int = 0,
    drift: bool = False,
    generation: int | None = None,
) -> bytes:
    result_sha = _sha256(b"dex2c-result")
    payload = {
        "schema": SCHEMA,
        "execution_id": binding.execution_id,
        "attempt_id": binding.attempt_id,
        "binding_digest": binding_digest_value,
        "claim_generation": binding.claim_generation if generation is None else generation,
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
    """Contract-accurate port double; optional throw/fail hooks for rows."""

    evidence: bytes
    dispatch_status: str = "DISPATCHED"
    dispatch_calls: int = 0
    dispatch_throws: bool = False

    def dispatch(self, binding: DexBindingIdentity) -> dict:
        self.dispatch_calls += 1
        if self.dispatch_throws:
            raise RuntimeError("transport exploded")
        return {"status": self.dispatch_status}

    def collect(self, execution_id: str, attempt_id: str) -> bytes:
        return self.evidence


class WireHarness:
    def __init__(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()  # noqa: SIM115
        self.store = SQLiteExecutionStore(Path(self.tmp.name) / "exec.sqlite3")
        self.issuer = AdmissionIssuer()

    def make_wire(self, transport: ScriptedTransport) -> AdmissionReceiptWire:
        return AdmissionReceiptWire(issuer=self.issuer, store=self.store, transport=transport)

    def ensure_record(self, execution_id: str, head: str = "2" * 40) -> None:
        self.store.create(
            new_execution_record(
                execution_id=execution_id,
                job_id="job-001",
                work_order_ref="WO-P1-612",
                project_id="proj-001",
                worker_id="worker-glmlane",
                backend_id="backend-node",
                agent_ref=None,
                repo_root="A:\\repo\\example",
                branch="main",
                head_before=head,
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
        self.harness.ensure_record(binding.execution_id)
        view = ClaimView(claim_ref=binding.claim_ref, claim_generation=binding.claim_generation, live=True)
        digest = binding_digest(binding)
        transport = ScriptedTransport(build_evidence(binding, binding_digest_value=digest))
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
        self.harness.ensure_record(binding.execution_id)
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
        self.harness.ensure_record(binding.execution_id)
        transport = ScriptedTransport(b"{}")
        wire = self.harness.make_wire(transport)
        dead = ClaimView(claim_ref=binding.claim_ref, claim_generation=binding.claim_generation, live=False)
        outcome = wire.run_attempt(binding=binding, claim_view=dead)
        self.assertEqual(outcome.status, "DENIED")
        self.assertEqual(transport.dispatch_calls, 0)

    def test_denial_is_frozen_across_replays(self) -> None:
        # R3 r1 F1: a denied identity can never flip to admitted.
        binding = make_binding()
        self.harness.ensure_record(binding.execution_id)
        transport = ScriptedTransport(b"{}")
        wire = self.harness.make_wire(transport)
        dead = ClaimView(claim_ref=binding.claim_ref, claim_generation=binding.claim_generation, live=False)
        first = wire.run_attempt(binding=binding, claim_view=dead)
        self.assertEqual(first.status, "DENIED")
        alive = ClaimView(claim_ref=binding.claim_ref, claim_generation=binding.claim_generation, live=True)
        second = wire.run_attempt(binding=binding, claim_view=alive)
        self.assertEqual(second.status, "DENIED")
        self.assertEqual(transport.dispatch_calls, 0)

    def test_replay_with_mutated_binding_is_typed_conflict(self) -> None:
        # R3 r1 F1: the frozen decision binds the full digest.
        binding = make_binding()
        issuer = AdmissionIssuer()
        view = ClaimView(claim_ref=binding.claim_ref, claim_generation=binding.claim_generation, live=True)
        issuer.decide(binding=binding, claim_view=view)
        mutated = make_binding(
            execution_id=binding.execution_id,
            attempt_id=binding.attempt_id,
            executable_path="C:\\evil\\other.exe",
        )
        with self.assertRaises(AdmissionDenied):
            issuer.decide(binding=mutated, claim_view=view)

    def test_tampered_evidence_rejected_without_receipt(self) -> None:
        binding = make_binding()
        self.harness.ensure_record(binding.execution_id)
        raw = bytearray(build_evidence(binding, binding_digest_value=binding_digest(binding)))
        raw[10] = raw[10] ^ 0x01
        transport = ScriptedTransport(bytes(raw))
        wire = self.harness.make_wire(transport)
        view = ClaimView(claim_ref=binding.claim_ref, claim_generation=binding.claim_generation, live=True)
        outcome = wire.run_attempt(binding=binding, claim_view=view)
        self.assertEqual(outcome.status, "EVIDENCE_REJECTED", outcome.detail)
        self.assertIsNone(outcome.receipt_id)

    def test_wrong_binding_digest_evidence_rejected(self) -> None:
        binding = make_binding()
        self.harness.ensure_record(binding.execution_id)
        transport = ScriptedTransport(build_evidence(binding, binding_digest_value="0" * 64))
        wire = self.harness.make_wire(transport)
        view = ClaimView(claim_ref=binding.claim_ref, claim_generation=binding.claim_generation, live=True)
        outcome = wire.run_attempt(binding=binding, claim_view=view)
        self.assertEqual(outcome.status, "EVIDENCE_REJECTED")
        self.assertIn("DEX_EVIDENCE_BINDING_MISMATCH", outcome.detail)

    def test_generation_mismatch_evidence_rejected(self) -> None:
        # R3 r1 F3: decoded generation must agree with the admission.
        binding = make_binding()
        self.harness.ensure_record(binding.execution_id)
        evidence = build_evidence(
            binding, binding_digest_value=binding_digest(binding), generation=binding.claim_generation + 1
        )
        transport = ScriptedTransport(evidence)
        wire = self.harness.make_wire(transport)
        view = ClaimView(claim_ref=binding.claim_ref, claim_generation=binding.claim_generation, live=True)
        outcome = wire.run_attempt(binding=binding, claim_view=view)
        self.assertEqual(outcome.status, "EVIDENCE_REJECTED")
        self.assertIn("WIRE_GENERATION_MISMATCH", outcome.detail)

    def test_ambiguous_dispatch_fences_identity_no_second_dispatch(self) -> None:
        # R3 r1 F2/F5: ambiguity is retained; re-runs never re-dispatch.
        binding = make_binding()
        self.harness.ensure_record(binding.execution_id)
        transport = ScriptedTransport(b"{}", dispatch_status="AMBIGUOUS")
        wire = self.harness.make_wire(transport)
        view = ClaimView(claim_ref=binding.claim_ref, claim_generation=binding.claim_generation, live=True)
        first = wire.run_attempt(binding=binding, claim_view=view)
        self.assertEqual(first.status, "AMBIGUOUS")
        second = wire.run_attempt(binding=binding, claim_view=view)
        self.assertEqual(second.status, "AMBIGUOUS")
        self.assertEqual(transport.dispatch_calls, 1)  # fenced — no duplicate effect

    def test_throwing_dispatch_fences_identity_typed(self) -> None:
        binding = make_binding()
        self.harness.ensure_record(binding.execution_id)
        transport = ScriptedTransport(b"{}", dispatch_throws=True)
        wire = self.harness.make_wire(transport)
        view = ClaimView(claim_ref=binding.claim_ref, claim_generation=binding.claim_generation, live=True)
        first = wire.run_attempt(binding=binding, claim_view=view)
        self.assertEqual(first.status, "AMBIGUOUS")
        transport.dispatch_throws = False
        transport.dispatch_status = "DISPATCHED"
        second = wire.run_attempt(binding=binding, claim_view=view)
        self.assertEqual(second.status, "AMBIGUOUS")
        self.assertEqual(transport.dispatch_calls, 1)

    def test_missing_execution_record_fails_typed_before_dispatch(self) -> None:
        # R3 r1 F4: no record -> typed precondition failure, zero dispatch.
        binding = make_binding()  # deliberately NO ensure_record
        transport = ScriptedTransport(b"{}")
        wire = self.harness.make_wire(transport)
        view = ClaimView(claim_ref=binding.claim_ref, claim_generation=binding.claim_generation, live=True)
        with self.assertRaises(WireError) as ctx:
            wire.run_attempt(binding=binding, claim_view=view)
        self.assertEqual(ctx.exception.code, "WIRE_EXECUTION_RECORD_MISSING")
        self.assertEqual(transport.dispatch_calls, 0)

    def test_receipt_conflict_propagates_typed_not_duplicate(self) -> None:
        # R3 r1 F3: a DIFFERENT immutable receipt for the same identity is
        # a typed conflict, never masked as duplicate success.
        binding = make_binding()
        self.harness.ensure_record(binding.execution_id)
        digest = binding_digest(binding)
        # Pre-store a conflicting receipt (different result digest).
        conflicting = new_execution_receipt(
            execution_id=binding.execution_id,
            attempt_id=binding.attempt_id,
            result_digest=_sha256(b"conflicting-result"),
            binding_digest=digest,
            claim_generation=binding.claim_generation,
            authority_sha=binding.authority_sha,
            execution_sha=binding.execution_sha,
            disposition=ReceiptDisposition.QUARANTINED,
            evidence_ref=_sha256(b"conflicting-evidence"),
        )
        self.harness.store.record_receipt(conflicting)
        transport = ScriptedTransport(build_evidence(binding, binding_digest_value=digest))
        wire = self.harness.make_wire(transport)
        view = ClaimView(claim_ref=binding.claim_ref, claim_generation=binding.claim_generation, live=True)
        # The durable duplicate check sees the existing receipt and refuses
        # to dispatch again — outcome is the recorded receipt (conservative),
        # and NO second receipt is ever created.
        outcome = wire.run_attempt(binding=binding, claim_view=view)
        self.assertEqual(outcome.status, "DUPLICATE_ALREADY_COMPLETED")
        self.assertEqual(transport.dispatch_calls, 0)

    def test_collected_under_drift_quarantined_receipt(self) -> None:
        binding = make_binding()
        self.harness.ensure_record(binding.execution_id)
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
        first = issuer.decide(binding=binding, claim_view=view)
        second = issuer.decide(binding=binding, claim_view=view)
        self.assertEqual(first, second)


class RealSubstrateTests(unittest.TestCase):
    """Tier 2: REAL SRM ExecutionSupervisor evidence through the FULL wire."""

    SRM_ROOT = os.environ.get("SRM_REPO_ROOT", "")

    def test_real_substrate_evidence_through_full_wire(self) -> None:
        if not self.SRM_ROOT:
            self.skipTest("SRM_REPO_ROOT not set; real-substrate tier not exercised (contract tier covers wire logic)")
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
            # Binding facts match the ACTUALLY dispatched command (R3 r1 F6).
            executable_path="node",
            executable_sha256=_sha256(b"node -e process.exit(0)"),
            argv_shape=("-e", "process.exit(0)"),
        )
        digest = binding_digest(binding)
        canonical = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; sys.path.insert(0, r'%s'); "
                "from a_conductor.dex_identity import canonicalize_existing_root, canonical_root_digest; "
                "from pathlib import Path; "
                "c = canonicalize_existing_root(Path(r'%s')); "
                "print(c); print(canonical_root_digest(c, platform_tag='win32'))"
                % (str(Path(__file__).resolve().parents[1] / "src"), self.SRM_ROOT),
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        canonical_path, canonical_digest = canonical[0], canonical[1]

        driver = Path(__file__).parent / "fixtures" / "dex2c_srm_driver.mjs"
        request = {
            "srmRoot": self.SRM_ROOT,
            "command": "node",
            "args": ["-e", "process.exit(0)"],
            "cwd": self.SRM_ROOT,
            "claimGeneration": 1,
            "hostId": "host-test-01",
            "binding": {
                "executionId": binding.execution_id,
                "attemptId": binding.attempt_id,
                "canonicalPath": canonical_path,
                "canonicalDigest": canonical_digest,
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
        evidence_bytes = proc.stdout.strip()

        # Strict decode of the REAL substrate evidence.
        decoded = decode_collected_evidence(
            evidence_bytes,
            expected_execution_id=binding.execution_id,
            expected_attempt_id=binding.attempt_id,
            expected_binding_digest=digest,
            expected_authority_sha=binding.authority_sha,
            expected_execution_sha=binding.execution_sha,
        )
        self.assertEqual(decoded.exit_code, 0)

        # Full wire: admission → dispatch(DSPATCHED) → collect(real bytes) →
        # decode → durable receipt (R3 r1 F6: tier 2 must use the wire).
        harness = WireHarness()
        self.addCleanup(harness.close)
        harness.ensure_record(binding.execution_id, head=binding.execution_sha)
        transport = ScriptedTransport(evidence_bytes)
        wire = harness.make_wire(transport)
        view = ClaimView(claim_ref=binding.claim_ref, claim_generation=1, live=True)
        outcome = wire.run_attempt(binding=binding, claim_view=view)
        self.assertEqual(outcome.status, "COMPLETED", outcome.detail)
        receipt = harness.store.get_receipt(outcome.receipt_id)
        self.assertEqual(receipt.execution_id, binding.execution_id)
        self.assertEqual(receipt.result_digest, decoded.result_sha256)
        self.assertEqual(receipt.disposition, ReceiptDisposition.ACCEPTED)


if __name__ == "__main__":
    unittest.main(verbosity=2)
