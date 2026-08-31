from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from threading import Barrier

import pytest

from a_conductor.elastic_worker_capacity import (
    ElasticCapacityError,
    ElasticCapacityOutcomeKind,
    ElasticCapacityPolicy,
    ElasticProvisionedWorker,
    ElasticWorkerCapacityCoordinator,
    ProvisioningReservationKind,
    ProvisioningReservationRecord,
    ProvisioningReservationResult,
    SQLiteWorkerProvisioningReservations,
)
from a_conductor.graph.scheduler import (
    BlockedReason,
    BlockedReasonKind,
    SchedulePlan,
)
from a_conductor.worker_candidate_assembly import WorkerSupplyRecord
from a_conductor.worker_lease import (
    LeaseMutationIntent,
    SQLiteWorkerLeaseStore,
    WorkerLeaseBroker,
    WorkerLeaseCandidate,
    WorkerLeaseRequest,
)


NOW = datetime(2026, 8, 31, 1, 0, tzinfo=timezone.utc)
HEAD = "a" * 40


def capacity_plan(kind: BlockedReasonKind = BlockedReasonKind.CAPACITY) -> SchedulePlan:
    return SchedulePlan(
        selected=(),
        blocked=(BlockedReason("node-1", "blocked", kind),),
        capacity_evidence="0/1",
    )


def lease_request() -> WorkerLeaseRequest:
    return WorkerLeaseRequest(
        session_id="session-1",
        task_id="task-1",
        project_id="project-1",
        ordered_worker_ids=("a-worker-01",),
        required_capabilities=("shell",),
        required_runtime_id="runtime-elastic",
        worktree=r"A:\Repo",
        branch="feat/test",
        expected_head=HEAD,
        mutation_intent=LeaseMutationIntent.MUTATION,
        allowed_scope=("src/**",),
        forbidden_scope=("secrets/**",),
        mutable_scope=("src/a.py",),
        lease_ttl_seconds=600,
    )


def candidate(worker_id: str = "a-worker-09") -> WorkerLeaseCandidate:
    return WorkerLeaseCandidate(
        worker_id=worker_id,
        state="READY",
        reserved=False,
        active_task=False,
        capabilities=("shell", "repo"),
        runtime_id="runtime-elastic",
        project_id="project-1",
        worktree=r"A:\Repo",
        branch="feat/test",
        head=HEAD,
        health_fresh=True,
        ownership_known=True,
        dirty_state="CLEAN",
        mutation_authorized=True,
    )


class FakeAssembler:
    def __init__(self, value: WorkerSupplyRecord | Exception) -> None:
        self.value = value
        self.calls: list[str] = []

    def assemble(self, worker_id: str) -> WorkerSupplyRecord:
        self.calls.append(worker_id)
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


class FakeProvisioner:
    def __init__(self, value: ElasticProvisionedWorker | Exception) -> None:
        self.value = value
        self.calls = []

    def provision(self, request):
        self.calls.append(request)
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


def supply(worker_id: str = "a-worker-09") -> WorkerSupplyRecord:
    from a_conductor.graph.scheduler import WorkerSnapshot

    return WorkerSupplyRecord(
        worker_id=worker_id,
        scheduler=WorkerSnapshot(
            worker_id=worker_id,
            state="READY",
            capabilities=("shell", "repo"),
            reserved=False,
            project="project-1",
            workspace=r"A:\Repo",
            mutation_authorized=True,
        ),
        candidate=candidate(worker_id),
        reason_code="READY",
    )


def make_coordinator(tmp_path: Path, *, provisioner=None, assembler=None, reservations=None):
    lease_store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    ids = iter((f"lease-{i}" for i in range(1, 20)))
    broker = WorkerLeaseBroker(
        store=lease_store,
        lease_id_factory=lambda: next(ids),
        clock=lambda: NOW,
    )
    active_reservations = reservations or SQLiteWorkerProvisioningReservations(lease_store)
    return ElasticWorkerCapacityCoordinator(
        broker=broker,
        reservations=active_reservations,
        provisioner=provisioner
        or FakeProvisioner(ElasticProvisionedWorker("a-worker-09", "serena-local")),
        candidate_assembler=assembler or FakeAssembler(supply()),
        reservation_id_factory=lambda: "provision-1",
        clock=lambda: NOW,
    ), active_reservations


def policy(*, enabled=True, limit=1, allow_remote=False):
    return ElasticCapacityPolicy(
        enabled=enabled,
        max_extra_workers=limit,
        permitted_runtime_kinds=("serena-local",),
        allow_remote_connector=allow_remote,
    )


def test_disabled_or_non_capacity_failure_never_calls_provisioner(tmp_path: Path) -> None:
    provisioner = FakeProvisioner(ElasticProvisionedWorker("a-worker-09", "serena-local"))
    service, _ = make_coordinator(tmp_path, provisioner=provisioner)

    disabled = service.expand(
        capacity_plan(), lease_request(), runtime_kind="serena-local", policy=policy(enabled=False)
    )
    assert disabled.kind is ElasticCapacityOutcomeKind.POLICY_DISABLED
    assert provisioner.calls == []

    blocked = service.expand(
        capacity_plan(BlockedReasonKind.IDENTITY),
        lease_request(),
        runtime_kind="serena-local",
        policy=policy(),
    )
    assert blocked.kind is ElasticCapacityOutcomeKind.NOT_CAPACITY_FAILURE
    assert provisioner.calls == []


def test_atomic_reservation_limit_one_has_one_winner_across_independent_connections(tmp_path: Path) -> None:
    store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    left = SQLiteWorkerProvisioningReservations(store)
    right = SQLiteWorkerProvisioningReservations(store)
    barrier = Barrier(2)

    def acquire(authority, reservation_id, session_id):
        barrier.wait()
        return authority.acquire(
            reservation_id=reservation_id,
            session_id=session_id,
            task_id=f"task-{session_id}",
            runtime_kind="serena-local",
            max_extra_workers=1,
            now=NOW,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(acquire, left, "r-1", "s-1")
        b = pool.submit(acquire, right, "r-2", "s-2")
        results = (a.result(), b.result())

    assert sum(item.kind is ProvisioningReservationKind.ACQUIRED for item in results) == 1
    assert sum(item.kind is ProvisioningReservationKind.LIMIT_WAIT for item in results) == 1
    assert len(left.list_consuming()) == 1


def test_capacity_exhaustion_provisions_reobserves_then_uses_existing_broker(tmp_path: Path) -> None:
    provisioner = FakeProvisioner(ElasticProvisionedWorker("a-worker-09", "serena-local"))
    assembler = FakeAssembler(supply("a-worker-09"))
    service, reservations = make_coordinator(
        tmp_path, provisioner=provisioner, assembler=assembler
    )

    outcome = service.expand(
        capacity_plan(), lease_request(), runtime_kind="serena-local", policy=policy()
    )

    assert outcome.kind is ElasticCapacityOutcomeKind.PROVISIONED_AND_LEASED
    assert outcome.worker_id == "a-worker-09"
    assert outcome.lease_outcome is not None
    assert outcome.lease_outcome.lease is not None
    assert outcome.lease_outcome.lease.worker_id == "a-worker-09"
    assert assembler.calls == ["a-worker-09"]
    assert provisioner.calls[0].remote_connector_allowed is False
    records = reservations.list_consuming()
    assert len(records) == 1
    assert records[0].state == "PROVISIONED"
    assert records[0].worker_id == "a-worker-09"


def test_provisioning_uncertainty_consumes_slot_and_prevents_blind_retry(tmp_path: Path) -> None:
    provisioner = FakeProvisioner(RuntimeError("transport lost after create"))
    service, reservations = make_coordinator(tmp_path, provisioner=provisioner)

    first = service.expand(
        capacity_plan(), lease_request(), runtime_kind="serena-local", policy=policy()
    )
    assert first.kind is ElasticCapacityOutcomeKind.RECOVERY_REQUIRED
    assert reservations.list_consuming()[0].state == "RECOVERY_REQUIRED"

    other_request = replace(lease_request(), session_id="session-2", task_id="task-2")
    second = service.expand(
        capacity_plan(), other_request, runtime_kind="serena-local", policy=policy()
    )
    assert second.kind is ElasticCapacityOutcomeKind.LIMIT_WAIT
    assert len(provisioner.calls) == 1


def test_unexpected_remote_connector_is_recovery_when_policy_does_not_allow_it(tmp_path: Path) -> None:
    provisioner = FakeProvisioner(
        ElasticProvisionedWorker(
            "a-worker-09", "serena-local", remote_connector_configured=True
        )
    )
    service, reservations = make_coordinator(tmp_path, provisioner=provisioner)

    outcome = service.expand(
        capacity_plan(), lease_request(), runtime_kind="serena-local", policy=policy()
    )

    assert outcome.kind is ElasticCapacityOutcomeKind.RECOVERY_REQUIRED
    assert outcome.reason_code == "REMOTE_CONNECTOR_UNAUTHORIZED"
    assert reservations.list_consuming()[0].state == "RECOVERY_REQUIRED"


def test_reobserved_worker_that_fails_existing_broker_is_not_silently_retried(tmp_path: Path) -> None:
    bad = supply("a-worker-09")
    bad = replace(bad, candidate=replace(bad.candidate, head="b" * 40))
    service, reservations = make_coordinator(
        tmp_path, assembler=FakeAssembler(bad)
    )

    outcome = service.expand(
        capacity_plan(), lease_request(), runtime_kind="serena-local", policy=policy()
    )

    assert outcome.kind is ElasticCapacityOutcomeKind.RECOVERY_REQUIRED
    assert outcome.reason_code == "PROVISIONED_WORKER_NOT_LEASED"
    assert reservations.list_consuming()[0].state == "PROVISIONED"


def test_runtime_kind_outside_policy_does_not_reserve_or_provision(tmp_path: Path) -> None:
    provisioner = FakeProvisioner(ElasticProvisionedWorker("a-worker-09", "serena-local"))
    service, reservations = make_coordinator(tmp_path, provisioner=provisioner)

    outcome = service.expand(
        capacity_plan(), lease_request(), runtime_kind="remote-chatgpt", policy=policy()
    )

    assert outcome.kind is ElasticCapacityOutcomeKind.POLICY_BLOCKED
    assert outcome.reason_code == "RUNTIME_KIND_NOT_ALLOWED"
    assert provisioner.calls == []
    assert reservations.list_consuming() == ()


def test_corrupt_persisted_reservation_text_is_typed_invalid_data(tmp_path: Path) -> None:
    store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    reservations = SQLiteWorkerProvisioningReservations(store)
    result = reservations.acquire(
        reservation_id="r-1",
        session_id="s-1",
        task_id="t-1",
        runtime_kind="serena-local",
        max_extra_workers=1,
        now=NOW,
    )
    assert result.record is not None
    with sqlite3.connect(store.database_path) as connection:
        connection.execute(
            "UPDATE worker_provisioning_reservations SET runtime_kind = ? WHERE reservation_id = ?",
            ("bad\nkind", "r-1"),
        )
        connection.commit()

    with pytest.raises(ElasticCapacityError, match="PROVISIONING_RECORD_INVALID"):
        reservations.list_consuming()


class BadReservationAuthority(SQLiteWorkerProvisioningReservations):
    def __init__(self, lease_store, result):
        super().__init__(lease_store)
        self.result = result

    def acquire(self, **kwargs):
        return self.result


def test_capacity_wait_reason_code_is_sanitized(tmp_path: Path) -> None:
    lease_store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    authority = BadReservationAuthority(
        lease_store,
        ProvisioningReservationResult(
            ProvisioningReservationKind.LIMIT_WAIT,
            None,
            "BAD\nREASON",
        ),
    )
    service, _ = make_coordinator(tmp_path, reservations=authority)

    outcome = service.expand(
        capacity_plan(), lease_request(), runtime_kind="serena-local", policy=policy()
    )
    assert outcome.kind is ElasticCapacityOutcomeKind.LIMIT_WAIT
    assert outcome.reason_code == "ELASTIC_CAPACITY_LIMIT_REACHED"


def test_acquired_reservation_identity_mismatch_fails_before_provisioner(tmp_path: Path) -> None:
    lease_store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    wrong = ProvisioningReservationRecord(
        reservation_id="different",
        session_id="wrong-session",
        task_id="wrong-task",
        runtime_kind="wrong-runtime",
        state="ACTIVE",
        worker_id=None,
        acquired_at="2026-08-31T01:00:00Z",
        updated_at="2026-08-31T01:00:00Z",
    )
    authority = BadReservationAuthority(
        lease_store,
        ProvisioningReservationResult(
            ProvisioningReservationKind.ACQUIRED,
            wrong,
            "PROVISIONING_RESERVED",
        ),
    )
    provisioner = FakeProvisioner(ElasticProvisionedWorker("a-worker-09", "serena-local"))
    service, _ = make_coordinator(
        tmp_path, reservations=authority, provisioner=provisioner
    )

    outcome = service.expand(
        capacity_plan(), lease_request(), runtime_kind="serena-local", policy=policy()
    )
    assert outcome.kind is ElasticCapacityOutcomeKind.RECOVERY_REQUIRED
    assert outcome.reason_code == "PROVISIONING_RESERVATION_IDENTITY_MISMATCH"
    assert provisioner.calls == []


def test_future_or_malformed_reservation_kind_fails_closed(tmp_path: Path) -> None:
    lease_store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    malformed = ProvisioningReservationResult(  # type: ignore[arg-type]
        "FUTURE_KIND",
        None,
        "future",
    )
    authority = BadReservationAuthority(lease_store, malformed)
    service, _ = make_coordinator(tmp_path, reservations=authority)

    outcome = service.expand(
        capacity_plan(), lease_request(), runtime_kind="serena-local", policy=policy()
    )
    assert outcome.kind is ElasticCapacityOutcomeKind.RECOVERY_REQUIRED
    assert outcome.reason_code == "PROVISIONING_RESERVATION_OUTCOME_UNSUPPORTED"
