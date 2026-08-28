"""Application facade over A-Conductor durable job runtime primitives.

This service deliberately contains no SQL, transition graph, command runner,
scheduler, planner, router, or UI/transport logic. It delegates durable state
to SQLiteJobStore and bounded execution to DurableJobExecutionCoordinator.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from .domain import TaskState
from .job_execution import DurableJobExecutionCoordinator, JobExecutionOutcome
from .job_state import JobRuntimeState
from .job_store import JobEvent, SQLiteJobStore
from .native_operation_assembly import (
    ControlCenterNativeAdapterResolver,
    ControlCenterSnapshotProvider,
)
from .native_operations import (
    AllowlistedNativeJobBackend,
    NativeOperationDefinition,
    NativeOperationRegistry,
    WorkerNativeAdapterResolver,
)


class DurableJobControlService:
    def __init__(
        self,
        *,
        store: SQLiteJobStore,
        coordinator: DurableJobExecutionCoordinator,
    ) -> None:
        self._store = store
        self._coordinator = coordinator

    @classmethod
    def open(
        cls,
        database_path: str | Path,
        *,
        operations: Sequence[NativeOperationDefinition],
        control_center: ControlCenterSnapshotProvider | None = None,
        native_resolver: WorkerNativeAdapterResolver | None = None,
        supervised: bool = False,
    ) -> "DurableJobControlService":
        if native_resolver is None:
            if control_center is None:
                raise ValueError(
                    "control_center is required when native_resolver is not injected"
                )
            if supervised:
                from .supervised_command_runner import (
                    build_supervised_native_adapter_resolver,
                )

                native_resolver = build_supervised_native_adapter_resolver(
                    service=control_center,
                    database_path=database_path,
                )
            else:
                native_resolver = ControlCenterNativeAdapterResolver(
                    service=control_center
                )
        store = SQLiteJobStore(database_path)
        registry = NativeOperationRegistry(tuple(operations))
        backend = AllowlistedNativeJobBackend(
            registry=registry,
            resolver=native_resolver,
        )
        coordinator = DurableJobExecutionCoordinator(
            store=store,
            backend=backend,
        )
        return cls(store=store, coordinator=coordinator)

    def create_job(
        self,
        *,
        job_id: str,
        work_order_ref: str,
        project_id: str,
        max_attempts: int = 3,
    ) -> JobRuntimeState:
        return self._store.create_job(
            job_id=job_id,
            work_order_ref=work_order_ref,
            project_id=project_id,
            max_attempts=max_attempts,
        )

    def get_job(self, job_id: str) -> JobRuntimeState:
        return self._store.get_job(job_id)

    def list_events(self, job_id: str) -> tuple[JobEvent, ...]:
        return self._store.list_events(job_id)

    def mark_ready(self, job_id: str, *, expected_version: int) -> JobRuntimeState:
        return self._store.transition(
            job_id,
            TaskState.READY,
            expected_version=expected_version,
        )

    def claim(
        self,
        job_id: str,
        *,
        expected_version: int,
        worker_id: str,
    ) -> JobRuntimeState:
        return self._store.transition(
            job_id,
            TaskState.CLAIMED,
            expected_version=expected_version,
            worker_id=worker_id,
        )

    def block(
        self,
        job_id: str,
        *,
        expected_version: int,
        worker_id: str,
        evidence_ref: str | None = None,
    ) -> JobRuntimeState:
        return self._store.transition(
            job_id,
            TaskState.BLOCKED,
            expected_version=expected_version,
            worker_id=worker_id,
            evidence_ref=evidence_ref,
        )

    def gate(
        self,
        job_id: str,
        *,
        expected_version: int,
        worker_id: str,
        evidence_ref: str | None = None,
    ) -> JobRuntimeState:
        return self._store.transition(
            job_id,
            TaskState.GATING,
            expected_version=expected_version,
            worker_id=worker_id,
            evidence_ref=evidence_ref,
        )

    def checkpoint(
        self,
        job_id: str,
        *,
        expected_version: int,
        checkpoint_ref: str,
        evidence_ref: str | None = None,
    ) -> JobRuntimeState:
        return self._store.checkpoint(
            job_id,
            expected_version=expected_version,
            checkpoint_ref=checkpoint_ref,
            evidence_ref=evidence_ref,
        )

    def execute_operation(
        self,
        job_id: str,
        *,
        expected_version: int,
        worker_id: str,
        operation_ref: str,
    ) -> JobExecutionOutcome:
        return self._coordinator.execute(
            job_id,
            expected_version=expected_version,
            worker_id=worker_id,
            operation_ref=operation_ref,
        )
