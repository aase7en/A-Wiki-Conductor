from __future__ import annotations

from datetime import datetime, timezone
import multiprocessing

import pytest

from a_conductor.elastic_worker_capacity import (
    ElasticCapacityError,
    SQLiteWorkerProvisioningReservations,
)
from a_conductor.worker_lease import SQLiteWorkerLeaseStore


NOW = datetime(2026, 8, 31, 1, 0, tzinfo=timezone.utc)


def _reserve_capacity_in_process(database, start_event, output, reservation_id, session_id):
    try:
        store = SQLiteWorkerLeaseStore(database)
        if not start_event.wait(10):
            output.put(("error", "start-timeout"))
            return
        result = store.acquire_provisioning_reservation(
            reservation_id=reservation_id,
            session_id=session_id,
            task_id=f"task-{session_id}",
            runtime_kind="serena-local",
            max_extra_workers=1,
            now="2026-08-31T01:00:00Z",
        )
        output.put(("ok", result.kind.value))
    except BaseException as exc:
        output.put(("error", f"{type(exc).__name__}:{exc}"))


def test_provisioning_transition_requires_exact_owner_task_identity(tmp_path) -> None:
    store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    reservations = SQLiteWorkerProvisioningReservations(store)
    acquired = reservations.acquire(
        reservation_id="reservation-1",
        session_id="session-1",
        task_id="task-1",
        runtime_kind="serena-local",
        max_extra_workers=1,
        now=NOW,
    )
    assert acquired.record is not None

    with pytest.raises(ElasticCapacityError, match="PROVISIONING_OWNER_MISMATCH"):
        reservations.mark_recovery(
            "reservation-1",
            session_id="other-session",
            task_id="task-1",
            now=NOW,
        )

    record = reservations.list_consuming()[0]
    assert record.state == "PRE_PROVISION"
    assert record.session_id == "session-1"
    assert record.task_id == "task-1"



def test_worker_lease_store_owns_provisioning_reservation_authority(tmp_path) -> None:
    store = SQLiteWorkerLeaseStore(tmp_path / "leases.sqlite")
    result = store.acquire_provisioning_reservation(
        reservation_id="reservation-1",
        session_id="session-1",
        task_id="task-1",
        runtime_kind="serena-local",
        max_extra_workers=1,
        now=NOW,
    )
    assert result.kind.value == "ACQUIRED"
    assert result.record is not None
    assert result.record.reservation_id == "reservation-1"
    assert store.list_provisioning_reservations(consuming_only=True) == (result.record,)


def test_capacity_limit_one_has_one_winner_across_spawned_processes(tmp_path) -> None:
    database = str(tmp_path / "leases.sqlite")
    SQLiteWorkerLeaseStore(database)
    ctx = multiprocessing.get_context("spawn")
    start_event = ctx.Event()
    output = ctx.Queue()
    processes = (
        ctx.Process(
            target=_reserve_capacity_in_process,
            args=(database, start_event, output, "reservation-a", "session-a"),
        ),
        ctx.Process(
            target=_reserve_capacity_in_process,
            args=(database, start_event, output, "reservation-b", "session-b"),
        ),
    )
    for process in processes:
        process.start()
    start_event.set()
    for process in processes:
        process.join(15)
        assert process.exitcode == 0
    results = [output.get(timeout=5) for _ in processes]
    assert all(status == "ok" for status, _ in results), results
    assert sorted(value for _, value in results) == ["ACQUIRED", "LIMIT_WAIT"]
    assert len(
        SQLiteWorkerLeaseStore(database).list_provisioning_reservations(
            consuming_only=True
        )
    ) == 1
