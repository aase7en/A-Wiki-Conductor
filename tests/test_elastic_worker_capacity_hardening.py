from __future__ import annotations

from datetime import datetime, timezone

import pytest

from a_conductor.elastic_worker_capacity import (
    ElasticCapacityError,
    SQLiteWorkerProvisioningReservations,
)
from a_conductor.worker_lease import SQLiteWorkerLeaseStore


NOW = datetime(2026, 8, 31, 1, 0, tzinfo=timezone.utc)


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
    assert record.state == "ACTIVE"
    assert record.session_id == "session-1"
    assert record.task_id == "task-1"
