"""DEX-2dA durability tests — durable admission journal + cross-restart fence (WO-P1-627).

Deterministic tier-1 matrix for the two WO-P1-625 §Limitations items closed by
this slice: (1) admission decisions survive issuer restart with the exact
in-process replay semantics; (2) a durable write-ahead fence committed before
dispatch makes every crash window (reserve→dispatch, dispatch→receipt,
ambiguity paths) at-most-once across NEW wire/issuer instances — the
in-process fence memory is deliberately discarded to simulate restart.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import tempfile
import threading
import unittest
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from a_conductor.dex_admission import (  # noqa: E402
    DENIED_IDENTITY_MISMATCH,
    AdmissionDenied,
    AdmissionIssuer,
    ClaimView,
    DurableAdmissionJournal,
)
from a_conductor.dex_identity import DexBindingIdentity, binding_digest  # noqa: E402
from a_conductor.dex_wire import AdmissionReceiptWire, WireError  # noqa: E402
from a_conductor.execution_record import (  # noqa: E402
    ExecutionProcessState,
    TransportState,
    new_execution_record,
)
from a_conductor.execution_store import (  # noqa: E402
    ExecutionStoreError,
    SQLiteExecutionStore,
)

SCHEMA = "dex.srm.collection.v1"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_binding(
    *,
    execution_id: str = "exec-dex2da-0001-a1",
    attempt_id: str = "attempt-0001-a1",
    claim_generation: int = 5,
    executable_path: str = "C:\\tools\\node.exe",
) -> DexBindingIdentity:
    return DexBindingIdentity(
        execution_id=execution_id,
        attempt_id=attempt_id,
        task_ref="task/dex2da-test",
        lane_ref="lane/dex2da",
        claim_ref="claim/dex2da-001",
        claim_generation=claim_generation,
        authority_repo_identity="aase7en/A-Wiki-Conductor",
        execution_repo_identity="aase7en/SunDayRemoteMCP",
        authority_sha="1" * 40,
        execution_sha="2" * 40,
        host_id="host-test-01",
        boot_id="boot-test-01",
        executable_path=executable_path,
        executable_sha256="3" * 64,
        argv_shape=("--version",),
    )


def build_evidence(
    binding: DexBindingIdentity,
    *,
    binding_digest_value: str,
    drift: bool = False,
) -> bytes:
    result_sha = _sha256(b"dex2da-result")
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
            "exit_code": 0,
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
    evidence: bytes
    dispatch_status: str = "DISPATCHED"
    dispatch_calls: int = 0
    dispatch_throws: bool = False
    collect_throws: bool = False
    # Test orchestration: dispatch_entered is set the moment dispatch() is
    # entered; dispatch_gate blocks INSIDE dispatch until opened. The gate
    # NEVER silently releases on timeout — a harness failure raises instead,
    # so a gated race cannot degrade into a time-dependent outcome.
    dispatch_gate: threading.Event | None = None
    dispatch_entered: threading.Event | None = None

    def dispatch(self, binding: DexBindingIdentity) -> dict:
        self.dispatch_calls += 1
        if self.dispatch_entered is not None:
            self.dispatch_entered.set()
        if self.dispatch_gate is not None:
            if not self.dispatch_gate.wait(timeout=60):
                raise AssertionError("dispatch gate never opened (test harness failure)")
        if self.dispatch_throws:
            raise RuntimeError("transport exploded")
        return {"status": self.dispatch_status}

    def collect(self, execution_id: str, attempt_id: str) -> bytes:
        if self.collect_throws:
            raise RuntimeError("collect exploded")
        return self.evidence


class DurableHarness:
    """One store file; issuers/wires are created per 'process lifetime'."""

    def __init__(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()  # noqa: SIM115
        self.store = SQLiteExecutionStore(Path(self.tmp.name) / "exec.sqlite3")
        self.journal = DurableAdmissionJournal(self.store)

    def restarted_issuer(self) -> AdmissionIssuer:
        return AdmissionIssuer(journal=self.journal)

    def restarted_wire(self, transport: ScriptedTransport) -> AdmissionReceiptWire:
        return AdmissionReceiptWire(
            issuer=self.restarted_issuer(), store=self.store, transport=transport
        )

    def ensure_record(self, execution_id: str) -> None:
        self.store.create(
            new_execution_record(
                execution_id=execution_id,
                job_id="job-001",
                work_order_ref="WO-P1-627",
                project_id="proj-001",
                worker_id="worker-glmlane",
                backend_id="backend-node",
                agent_ref=None,
                repo_root="A:\\repo\\example",
                branch="main",
                head_before="2" * 40,
                operation_ref="op-001",
                command_fingerprint="f" * 64,
                command_summary="dex2da test attempt",
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


class AdmissionJournalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.harness = DurableHarness()
        self.addCleanup(self.harness.close)

    def test_admission_survives_issuer_restart(self) -> None:
        binding = make_binding()
        view = ClaimView(claim_ref=binding.claim_ref, claim_generation=binding.claim_generation, live=True)
        first = self.harness.restarted_issuer().decide(binding=binding, claim_view=view)
        # A brand-new issuer instance (simulated restart) over the same journal.
        second = self.harness.restarted_issuer().decide(binding=binding, claim_view=view)
        self.assertEqual(first, second)

    def test_denial_survives_issuer_restart(self) -> None:
        binding = make_binding()
        dead = ClaimView(claim_ref=binding.claim_ref, claim_generation=binding.claim_generation, live=False)
        with self.assertRaises(AdmissionDenied):
            self.harness.restarted_issuer().decide(binding=binding, claim_view=dead)
        alive = ClaimView(claim_ref=binding.claim_ref, claim_generation=binding.claim_generation, live=True)
        with self.assertRaises(AdmissionDenied) as ctx:
            self.harness.restarted_issuer().decide(binding=binding, claim_view=alive)
        self.assertEqual(ctx.exception.code, "ADMISSION_CLAIM_NOT_LIVE")

    def test_replay_with_mutated_binding_across_restart_typed(self) -> None:
        binding = make_binding()
        view = ClaimView(claim_ref=binding.claim_ref, claim_generation=binding.claim_generation, live=True)
        self.harness.restarted_issuer().decide(binding=binding, claim_view=view)
        mutated = make_binding(executable_path="C:\\evil\\other.exe")
        with self.assertRaises(AdmissionDenied) as ctx:
            self.harness.restarted_issuer().decide(binding=mutated, claim_view=view)
        self.assertEqual(ctx.exception.code, DENIED_IDENTITY_MISMATCH)

    def test_replay_with_different_generation_across_restart_typed(self) -> None:
        binding = make_binding()
        view = ClaimView(claim_ref=binding.claim_ref, claim_generation=binding.claim_generation, live=True)
        self.harness.restarted_issuer().decide(binding=binding, claim_view=view)
        other = ClaimView(claim_ref=binding.claim_ref, claim_generation=binding.claim_generation + 1, live=True)
        with self.assertRaises(AdmissionDenied) as ctx:
            self.harness.restarted_issuer().decide(binding=binding, claim_view=other)
        self.assertEqual(ctx.exception.code, DENIED_IDENTITY_MISMATCH)

    def test_journal_record_idempotent_and_conflict_typed(self) -> None:
        from a_conductor.execution_store import AdmissionDecisionRow

        binding = make_binding()
        digest = binding_digest(binding)
        row = AdmissionDecisionRow(
            execution_id=binding.execution_id,
            attempt_id=binding.attempt_id,
            binding_digest=digest,
            claim_ref=binding.claim_ref,
            claim_generation=binding.claim_generation,
            admitted=True,
            code=None,
            detail=None,
        )
        self.harness.store.record_admission_decision(row)  # initial record
        self.harness.store.record_admission_decision(row)  # identical re-record: no-op
        conflicting = AdmissionDecisionRow(
            execution_id=binding.execution_id,
            attempt_id=binding.attempt_id,
            binding_digest=digest,
            claim_ref=binding.claim_ref,
            claim_generation=binding.claim_generation,
            admitted=False,
            code="ADMISSION_CLAIM_NOT_LIVE",
            detail="different decision for the same identity",
        )
        with self.assertRaises(ExecutionStoreError) as ctx:
            self.harness.store.record_admission_decision(conflicting)
        self.assertIn("ADMISSION_DECISION_CONFLICT", str(ctx.exception))

    def test_stale_generation_denial_persists_and_blocks_new_attempts(self) -> None:
        binding = make_binding(claim_generation=3)
        view = ClaimView(claim_ref=binding.claim_ref, claim_generation=9, live=True)
        with self.assertRaises(AdmissionDenied) as ctx:
            self.harness.restarted_issuer().decide(binding=binding, claim_view=view)
        self.assertEqual(ctx.exception.code, "ADMISSION_CLAIM_GENERATION_STALE")
        # The frozen denial survives restart: the SAME view re-raises the
        # SAME denial code, and ANY other presented generation for the
        # decided identity is a typed replay conflict — the identity is
        # blocked either way, never re-decided.
        with self.assertRaises(AdmissionDenied) as ctx2:
            self.harness.restarted_issuer().decide(binding=binding, claim_view=view)
        self.assertEqual(ctx2.exception.code, "ADMISSION_CLAIM_GENERATION_STALE")
        other = ClaimView(claim_ref=binding.claim_ref, claim_generation=3, live=True)
        with self.assertRaises(AdmissionDenied) as ctx3:
            self.harness.restarted_issuer().decide(binding=binding, claim_view=other)
        self.assertEqual(ctx3.exception.code, DENIED_IDENTITY_MISMATCH)

    def test_tampered_float_generation_is_corrupt_not_normalized(self) -> None:
        # R3 r1 F1 (P1): a tampered journal value (REAL claim_generation)
        # must surface as typed corruption — int()/bool() coercion must
        # never normalize it into a valid admission.
        binding = make_binding()
        view = ClaimView(claim_ref=binding.claim_ref, claim_generation=binding.claim_generation, live=True)
        self.harness.restarted_issuer().decide(binding=binding, claim_view=view)
        conn = sqlite3.connect(Path(self.harness.tmp.name) / "exec.sqlite3")
        try:
            conn.execute(
                "UPDATE admission_decisions SET claim_generation = 5.5 "
                "WHERE execution_id = ? AND attempt_id = ?",
                (binding.execution_id, binding.attempt_id),
            )
            conn.commit()
        finally:
            conn.close()
        with self.assertRaises(ExecutionStoreError) as ctx:
            self.harness.restarted_issuer().decide(binding=binding, claim_view=view)
        self.assertIn("ADMISSION_JOURNAL_CORRUPT", str(ctx.exception))


class CrossRestartFenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.harness = DurableHarness()
        self.addCleanup(self.harness.close)
        self.binding = make_binding()
        self.harness.ensure_record(self.binding.execution_id)
        self.view = ClaimView(
            claim_ref=self.binding.claim_ref,
            claim_generation=self.binding.claim_generation,
            live=True,
        )
        self.digest = binding_digest(self.binding)

    def _evidence(self) -> bytes:
        return build_evidence(self.binding, binding_digest_value=self.digest)

    def test_success_then_restart_returns_duplicate_receipt(self) -> None:
        transport = ScriptedTransport(self._evidence())
        first = self.harness.restarted_wire(transport)
        outcome = first.run_attempt(binding=self.binding, claim_view=self.view)
        self.assertEqual(outcome.status, "COMPLETED", outcome.detail)
        # Restarted wire (fresh in-process fence memory) over the same store.
        transport2 = ScriptedTransport(self._evidence())
        again = self.harness.restarted_wire(transport2)
        outcome2 = again.run_attempt(binding=self.binding, claim_view=self.view)
        self.assertEqual(outcome2.status, "DUPLICATE_ALREADY_COMPLETED")
        self.assertEqual(outcome2.receipt_id, outcome.receipt_id)
        self.assertEqual(transport2.dispatch_calls, 0)

    def test_crash_after_reserve_before_dispatch(self) -> None:
        # dispatch throws AFTER the durable reservation was committed.
        transport = ScriptedTransport(self._evidence(), dispatch_throws=True)
        wire = self.harness.restarted_wire(transport)
        first = wire.run_attempt(binding=self.binding, claim_view=self.view)
        self.assertEqual(first.status, "AMBIGUOUS")
        self.assertEqual(transport.dispatch_calls, 1)
        # "Restart": new wire + healthy transport. The durable fence (not the
        # dead in-process set) must block any second dispatch.
        transport2 = ScriptedTransport(self._evidence())
        second = self.harness.restarted_wire(transport2)
        outcome = second.run_attempt(binding=self.binding, claim_view=self.view)
        self.assertEqual(outcome.status, "AMBIGUOUS")
        self.assertEqual(transport2.dispatch_calls, 0)

    def test_crash_after_dispatch_before_receipt(self) -> None:
        transport = ScriptedTransport(self._evidence(), collect_throws=True)
        wire = self.harness.restarted_wire(transport)
        with self.assertRaises(WireError):
            wire.run_attempt(binding=self.binding, claim_view=self.view)
        self.assertEqual(transport.dispatch_calls, 1)
        transport2 = ScriptedTransport(self._evidence())
        second = self.harness.restarted_wire(transport2)
        outcome = second.run_attempt(binding=self.binding, claim_view=self.view)
        self.assertEqual(outcome.status, "AMBIGUOUS")
        self.assertEqual(transport2.dispatch_calls, 0)

    def test_evidence_rejection_durally_fenced(self) -> None:
        raw = bytearray(self._evidence())
        raw[10] = raw[10] ^ 0x01
        transport = ScriptedTransport(bytes(raw))
        wire = self.harness.restarted_wire(transport)
        first = wire.run_attempt(binding=self.binding, claim_view=self.view)
        self.assertEqual(first.status, "EVIDENCE_REJECTED")
        transport2 = ScriptedTransport(self._evidence())
        second = self.harness.restarted_wire(transport2)
        outcome = second.run_attempt(binding=self.binding, claim_view=self.view)
        self.assertEqual(outcome.status, "AMBIGUOUS")
        self.assertEqual(transport2.dispatch_calls, 0)

    def test_abandoned_reserved_blocks_restart(self) -> None:
        # Abrupt termination between the reservation commit and dispatch:
        # no exception handler ran, so the fence is left RESERVED. (The
        # abandoned state is constructed directly because a test process
        # cannot be killed mid-window; the durable state is identical.)
        self.harness.store.reserve_dispatch_fence(
            self.binding.execution_id, self.binding.attempt_id, self.digest
        )
        transport = ScriptedTransport(self._evidence())
        restarted = self.harness.restarted_wire(transport)
        outcome = restarted.run_attempt(binding=self.binding, claim_view=self.view)
        self.assertEqual(outcome.status, "AMBIGUOUS")
        self.assertEqual(transport.dispatch_calls, 0)

    def test_abandoned_dispatched_without_receipt_blocks_restart(self) -> None:
        # Abrupt termination after substrate acceptance but before any
        # receipt: the fence is left DISPATCHED.
        self.harness.store.reserve_dispatch_fence(
            self.binding.execution_id, self.binding.attempt_id, self.digest
        )
        self.harness.store.transition_dispatch_fence(
            self.binding.execution_id, self.binding.attempt_id, "DISPATCHED", "abandoned mid-flight"
        )
        transport = ScriptedTransport(self._evidence())
        restarted = self.harness.restarted_wire(transport)
        outcome = restarted.run_attempt(binding=self.binding, claim_view=self.view)
        self.assertEqual(outcome.status, "AMBIGUOUS")
        self.assertEqual(transport.dispatch_calls, 0)

    def test_retired_without_receipt_fails_closed(self) -> None:
        # RETIRED is only written after a verified receipt, so this state
        # without one is inconsistent — it must still fail closed, never
        # re-open the dispatch window.
        self.harness.store.reserve_dispatch_fence(
            self.binding.execution_id, self.binding.attempt_id, self.digest
        )
        self.harness.store.transition_dispatch_fence(
            self.binding.execution_id, self.binding.attempt_id, "RETIRED", "inconsistent"
        )
        transport = ScriptedTransport(self._evidence())
        restarted = self.harness.restarted_wire(transport)
        outcome = restarted.run_attempt(binding=self.binding, claim_view=self.view)
        self.assertEqual(outcome.status, "AMBIGUOUS")
        self.assertEqual(transport.dispatch_calls, 0)

    def test_fence_mark_conflict_keeps_wire_code(self) -> None:
        # R3 r1 F7: a fence-level transition conflict surfacing after
        # substrate acceptance must keep its conflict class
        # (WIRE_FENCE_CONFLICT), not collapse to WIRE_STATE_UNAVAILABLE.
        from a_conductor.dex_wire import WIRE_FENCE_CONFLICT

        transport = ScriptedTransport(self._evidence())
        wire = self.harness.restarted_wire(transport)
        original = self.harness.store.transition_dispatch_fence

        def conflicting_transition(execution_id, attempt_id, new_state, reason=None):
            if new_state == "DISPATCHED":
                raise ExecutionStoreError("FENCE_STATE_CONFLICT")
            return original(execution_id, attempt_id, new_state, reason)

        self.harness.store.transition_dispatch_fence = conflicting_transition  # type: ignore[method-assign]
        try:
            with self.assertRaises(WireError) as ctx:
                wire.run_attempt(binding=self.binding, claim_view=self.view)
            self.assertEqual(ctx.exception.code, WIRE_FENCE_CONFLICT)
        finally:
            self.harness.store.transition_dispatch_fence = original  # type: ignore[method-assign]
        self.assertEqual(transport.dispatch_calls, 1)  # dispatch DID happen; mark failed typed

    def test_fence_binding_conflict_typed_no_dispatch(self) -> None:
        # A different binding digest under the same identity must never
        # silently take over the fenced dispatch window. Two layers:
        # (a) a journal-backed replay of the mutated binding is DENIED by
        #     the frozen admission decision itself;
        # (b) even a journal-less fresh issuer (mismatched control-plane
        #     client) is rejected by the durable fence, typed, zero dispatch.
        transport = ScriptedTransport(self._evidence(), dispatch_throws=True)
        wire = self.harness.restarted_wire(transport)
        wire.run_attempt(binding=self.binding, claim_view=self.view)  # reserves + fences
        mutated = make_binding(executable_path="C:\\evil\\other.exe")
        mutated_view = ClaimView(
            claim_ref=mutated.claim_ref, claim_generation=mutated.claim_generation, live=True
        )
        # (a) journal-backed replay of a mutated binding: frozen denial.
        replay_transport = ScriptedTransport(
            build_evidence(mutated, binding_digest_value=binding_digest(mutated))
        )
        replay_outcome = self.harness.restarted_wire(replay_transport).run_attempt(
            binding=mutated, claim_view=mutated_view
        )
        self.assertEqual(replay_outcome.status, "DENIED")
        self.assertEqual(replay_transport.dispatch_calls, 0)
        # (b) fresh journal-less issuer: the durable fence must refuse.
        transport2 = ScriptedTransport(build_evidence(mutated, binding_digest_value=binding_digest(mutated)))
        attacker = AdmissionReceiptWire(
            issuer=AdmissionIssuer(), store=self.harness.store, transport=transport2
        )
        with self.assertRaises(WireError) as ctx:
            attacker.run_attempt(binding=mutated, claim_view=mutated_view)
        self.assertIn("FENCE_BINDING_CONFLICT", str(ctx.exception))
        self.assertEqual(transport2.dispatch_calls, 0)

    def test_two_connection_race_single_dispatch(self) -> None:
        # Two stores over one database file = two-connection proxy for two
        # processes (single-SQLite-file serialization boundary — NOT a
        # multi-host claim). Part 1: barrier-synchronized DIRECT reserve
        # contention — exactly one created=True. Part 2: a wire whose
        # dispatch is gated proves the reservation loser never dispatches
        # while the winner is mid-flight, deterministically AMBIGUOUS.
        store2 = SQLiteExecutionStore(Path(self.harness.tmp.name) / "exec.sqlite3")
        journal2 = DurableAdmissionJournal(store2)
        binding_b = make_binding(execution_id="exec-dex2da-race-b", attempt_id="attempt-race-b")
        self.harness.ensure_record(binding_b.execution_id)
        digest_b = binding_digest(binding_b)

        barrier = threading.Barrier(2)
        results: list = []

        def reserve(store) -> None:
            barrier.wait(timeout=30)
            results.append(
                store.reserve_dispatch_fence(
                    binding_b.execution_id, binding_b.attempt_id, digest_b
                )
            )

        workers = [
            threading.Thread(target=reserve, args=(self.harness.store,)),
            threading.Thread(target=reserve, args=(store2,)),
        ]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=30)
        created_flags = [created for _state, created in results]
        self.assertEqual(sorted(created_flags), [False, True])  # exactly one winner

        # Part 2: gated dispatch race on a fresh identity. B runs strictly
        # while A is provably INSIDE dispatch (entered-event wait, bounded;
        # the gate cannot silently release; cleanup is finally-guaranteed).
        binding_c = make_binding(execution_id="exec-dex2da-race-c", attempt_id="attempt-race-c")
        self.harness.ensure_record(binding_c.execution_id)
        digest_c = binding_digest(binding_c)
        view_c = ClaimView(claim_ref=binding_c.claim_ref, claim_generation=binding_c.claim_generation, live=True)
        gate = threading.Event()
        entered = threading.Event()
        transport_a = ScriptedTransport(
            build_evidence(binding_c, binding_digest_value=digest_c),
            dispatch_gate=gate,
            dispatch_entered=entered,
        )
        transport_b = ScriptedTransport(build_evidence(binding_c, binding_digest_value=digest_c))
        wire_a = AdmissionReceiptWire(
            issuer=AdmissionIssuer(journal=self.harness.journal),
            store=self.harness.store,
            transport=transport_a,
        )
        wire_b = AdmissionReceiptWire(
            issuer=AdmissionIssuer(journal=journal2), store=store2, transport=transport_b
        )
        result_a: list = []

        def run_a() -> None:
            result_a.append(wire_a.run_attempt(binding=binding_c, claim_view=view_c))

        worker = threading.Thread(target=run_a)
        worker.start()
        try:
            # Bounded wait until A is provably inside dispatch (its
            # reservation is committed and it holds the window). A
            # pre-dispatch failure in A surfaces here as a loud assert,
            # never an infinite poll.
            self.assertTrue(entered.wait(timeout=30), "wire A never entered dispatch")
            # B runs while A is blocked inside dispatch — no receipt can
            # exist, so B's only lawful outcome is the durable-fence
            # AMBIGUOUS. The gate only opens in the finally below, after
            # B's outcome is captured, so this is event-ordered, not
            # time-dependent.
            outcome_b = wire_b.run_attempt(binding=binding_c, claim_view=view_c)
        finally:
            gate.set()
            worker.join(timeout=60)
        self.assertFalse(worker.is_alive())
        self.assertEqual(outcome_b.status, "AMBIGUOUS")
        self.assertEqual(transport_a.dispatch_calls, 1)
        self.assertEqual(transport_b.dispatch_calls, 0)
        self.assertEqual(result_a[0].status, "COMPLETED", result_a[0].detail)

    def test_receipt_idempotent_same_wire_with_journal(self) -> None:
        transport = ScriptedTransport(self._evidence())
        wire = self.harness.restarted_wire(transport)
        first = wire.run_attempt(binding=self.binding, claim_view=self.view)
        again = wire.run_attempt(binding=self.binding, claim_view=self.view)
        self.assertEqual(again.status, "DUPLICATE_ALREADY_COMPLETED")
        self.assertEqual(again.receipt_id, first.receipt_id)
        self.assertEqual(transport.dispatch_calls, 1)

    def test_corrupted_store_fails_closed(self) -> None:
        self.harness.restarted_issuer().decide(binding=self.binding, claim_view=self.view)
        # Corrupt the database file in place (store connections are
        # per-operation and closed, so no handle blocks the write).
        db_path = Path(self.harness.tmp.name) / "exec.sqlite3"
        with open(db_path, "r+b") as fh:
            fh.seek(0)
            fh.write(b"not a sqlite database at all..............")
        fresh = SQLiteExecutionStore(db_path)
        journal = DurableAdmissionJournal(fresh)
        transport = ScriptedTransport(self._evidence())
        wire = AdmissionReceiptWire(
            issuer=AdmissionIssuer(journal=journal), store=fresh, transport=transport
        )
        with self.assertRaises((WireError, ExecutionStoreError)):
            wire.run_attempt(binding=self.binding, claim_view=self.view)
        self.assertEqual(transport.dispatch_calls, 0)  # never dispatched on unreadable state


class FenceTransitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.harness = DurableHarness()
        self.addCleanup(self.harness.close)

    def test_reserve_and_legal_transitions(self) -> None:
        state, created = self.harness.store.reserve_dispatch_fence("exec-t-01", "attempt-t-01", "a" * 64)
        self.assertEqual((state, created), ("RESERVED", True))
        state, created = self.harness.store.reserve_dispatch_fence("exec-t-01", "attempt-t-01", "a" * 64)
        self.assertEqual((state, created), ("RESERVED", False))  # existing row observed
        self.harness.store.transition_dispatch_fence("exec-t-01", "attempt-t-01", "DISPATCHED")
        self.harness.store.transition_dispatch_fence("exec-t-01", "attempt-t-01", "RETIRED")
        row = self.harness.store.load_dispatch_fence("exec-t-01", "attempt-t-01")
        self.assertIsNotNone(row)
        self.assertEqual(row.state, "RETIRED")

    def test_illegal_transitions_typed(self) -> None:
        self.harness.store.reserve_dispatch_fence("exec-t-02", "attempt-t-02", "b" * 64)
        with self.assertRaises(ExecutionStoreError) as ctx:
            self.harness.store.transition_dispatch_fence("exec-t-02", "attempt-t-02", "RETIRED2")
        self.assertIn("FENCE_STATE_CONFLICT", str(ctx.exception))
        self.harness.store.transition_dispatch_fence("exec-t-02", "attempt-t-02", "DISPATCHED")
        self.harness.store.transition_dispatch_fence("exec-t-02", "attempt-t-02", "FENCED")
        with self.assertRaises(ExecutionStoreError) as ctx2:
            self.harness.store.transition_dispatch_fence("exec-t-02", "attempt-t-02", "RETIRED")
        self.assertIn("FENCE_STATE_CONFLICT", str(ctx2.exception))  # FENCED is terminal

    def test_missing_fence_transition_typed(self) -> None:
        with self.assertRaises(ExecutionStoreError) as ctx:
            self.harness.store.transition_dispatch_fence("exec-t-03", "attempt-t-03", "DISPATCHED")
        self.assertIn("DISPATCH_FENCE_NOT_FOUND", str(ctx.exception))

    def test_reserve_binding_conflict_typed(self) -> None:
        self.harness.store.reserve_dispatch_fence("exec-t-04", "attempt-t-04", "c" * 64)
        with self.assertRaises(ExecutionStoreError) as ctx:
            self.harness.store.reserve_dispatch_fence("exec-t-04", "attempt-t-04", "d" * 64)
        self.assertIn("FENCE_BINDING_CONFLICT", str(ctx.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
