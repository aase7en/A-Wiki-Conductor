"""One explicitly admitted review batch. No scheduler, store, retry or lock.

Application ports are trusted dependencies, never external admission receipts.
Worker duplicate preflight delegates to the existing durable executor admission;
Parent evidence is never forged to make a worker signal pass the pipeline.
"""
from __future__ import annotations

import re
from contextvars import ContextVar
from dataclasses import dataclass, replace
from typing import Protocol

from .a_faster_utilization_guard import UtilizationFacts
from .claude_code_harness import MutationIntent
from .domain import TaskState
from .graph.dispatch import GraphDispatchAction, GraphDispatchResult
from .graph.scheduler import SchedulePlan
from .orchestration import OrchestrationError, decode_signal, encode_signal
from .orchestration_guards import GuardPipeline
from .orchestration_receiver import SignalReceiver
from .parallel_ready_execution import ParallelReadyOutcomeKind, ParallelReadyTask
from .pre_dispatch_guard import (
    PreDispatchGuardDecision, PreDispatchGuardDecisionKind,
    WorkerLeasePreDispatchGuard, live_worktree_drift_reason,
)
from .provider_execution_authority import ProviderExecutionAuthority
from .worker_lease import LeaseMutationIntent


def _ref(value):
    return (type(value) is str and 1 <= len(value) <= 256
            and all(33 <= ord(c) <= 126 for c in value))


def _reason(value, fallback="ORCH_WORKER_AUTHORITY_UNAVAILABLE"):
    return value if type(value) is str and re.fullmatch(r"[A-Z0-9_]{3,128}", value) else fallback


@dataclass(frozen=True, slots=True)
class WorkerIntent:
    task_ref: str
    intent_ref: str
    task_class: str
    project_id: str
    scope: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WorkerBatch:
    ready_plan_ref: str
    task_map_ref: str
    ready_generation: str
    plan: SchedulePlan
    tasks: tuple[ParallelReadyTask, ...]
    utilization_facts: UtilizationFacts
    evidence_refs: tuple[str, ...]


class WorkerAuthority(Protocol):
    """Readers must resolve exact canonical refs and fresh scheduler evidence."""
    def read_intent(self, signal) -> WorkerIntent: ...
    def read_batch(self, signal) -> WorkerBatch: ...
    def check(self, task_ref, scope) -> bool | None: ...
    def check_at_use(self, signal, baseline: WorkerIntent) -> PreDispatchGuardDecision: ...


@dataclass(frozen=True, slots=True)
class DispatchResult:
    signal_id: str
    kind: str
    task_ref: str
    decision: str
    reason_code: str
    subject_ids: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    execution_ids: tuple[str, ...] = ()
    submission_ids: tuple[str, ...] = ()
    observability_degraded: bool = False

    def __post_init__(self):
        if self.decision not in ("OBSERVED_ONLY", "NO_ACTION", "DENIED",
                "RECONCILIATION_REQUIRED", "SUBMISSION_OBSERVED", "DISPATCH_OBSERVED"):
            raise ValueError("ORCH_WORKER_BINDING_INVALID")
        if _reason(self.reason_code, "") != self.reason_code:
            raise ValueError("ORCH_WORKER_BINDING_INVALID")
        if not all(_ref(v) for v in (self.signal_id, self.kind, self.task_ref)):
            raise ValueError("ORCH_WORKER_BINDING_INVALID")
        for refs in (self.subject_ids, self.evidence_refs, self.execution_ids, self.submission_ids):
            if type(refs) is not tuple or len(refs) > 16 or not all(_ref(v) for v in refs):
                raise ValueError("ORCH_WORKER_BINDING_INVALID")
        if type(self.observability_degraded) is not bool:
            raise ValueError("ORCH_WORKER_BINDING_INVALID")


class _UseGateRunner:
    """Bound once per invocation; the existing executor retains uncertain leases."""
    def __init__(self, *, runner, authority, signal, intent, batch, jobs,
                 expected_job, providers, leases, observer, clock):
        self.runner, self.authority = runner, authority
        self.signal, self.intent, self.batch = signal, intent, batch
        self.jobs, self.expected_job = jobs, expected_job
        self.providers, self.leases = providers, leases
        self.observer, self.clock = observer, clock

    def check(self, task, lease, *, check_job=True):
        def deny(reason):
            raise OrchestrationError(_reason(reason, "ORCH_WORKER_USE_DENIED"))

        verdict = self.authority.check_at_use(self.signal, self.intent)
        if type(verdict) is not PreDispatchGuardDecision:
            deny("ORCH_WORKER_USE_DENIED")
        if verdict.kind is not PreDispatchGuardDecisionKind.ALLOW:
            deny(verdict.reason_code)
        if (self.authority.read_intent(self.signal) != self.intent
                or self.authority.read_batch(self.signal) != self.batch):
            deny("ORCH_WORKER_BINDING_DRIFT")
        if check_job and self.jobs.get_job(task.dispatch_request.key.job_id) != self.expected_job:
            deny("JOB_VERSION_CONFLICT")
        provider = ProviderExecutionAuthority(self.providers).authorize(
            task.provider_requirement, now=self.clock(), require_quota=task.require_quota)
        if not provider.allowed:
            deny(provider.reason_code)
        guard = WorkerLeasePreDispatchGuard(health_reader=self.leases,
            baseline_lease=lease, clock=self.clock).check()
        if guard.kind is not PreDispatchGuardDecisionKind.ALLOW:
            deny(guard.reason_code)
        request = task.lease_request
        reason = live_worktree_drift_reason(self.observer.observe(request.worktree),
            expected_repo_root=request.worktree, expected_branch=request.branch,
            expected_head=request.expected_head)
        if reason:
            deny(reason)

    def check_backend(self, context):
        task = self.batch.tasks[0]
        self.check(task, self._lease, check_job=False)
        job = self.jobs.get_job(context.job_id)
        if (job != self.executing_job
                or context.job_id != self.expected_job.job_id or job.state is not TaskState.EXECUTING
                or job.worker_id != self._lease.worker_id
                or context.worker_id != self._lease.worker_id
                or context.attempt_no != self.expected_job.attempt_count + 1):
            raise OrchestrationError("ORCH_WORKER_USE_DENIED")

    def run(self, task, lease):
        self.check(task, lease)
        self._lease = lease
        return self.runner.run(task, lease)


class Dispatcher:
    """Bounded application entry; never accepts a caller-supplied guard PASS."""
    def __init__(self, *, authority, jobs, executor_factory, trusted_source,
                 review_worker_id, review_provider_id, publisher=None):
        if (not all(callable(getattr(authority, name, None)) for name in
                    ("read_intent", "read_batch", "check", "check_at_use"))
                or not callable(executor_factory) or not all(_ref(v) for v in
                    (trusted_source, review_worker_id, review_provider_id))
                or (publisher is not None and not callable(publisher))):
            raise ValueError("ORCH_EXECUTOR_REQUIRED")
        self._authority, self._jobs = authority, jobs
        self._executor_factory, self._source = executor_factory, trusted_source
        self._publisher = publisher
        self._worker_id, self._provider_id = review_worker_id, review_provider_id
        self._handling = ContextVar("orch_worker_handling", default=False)
        # Worker target causes NOT_APPLICABLE before these Parent-only readers.
        self._receiver = SignalReceiver(queue_reader=None, turn_reader=None,
            binding_reader=lambda *_: None, clock=lambda: None)

    def handle(self, signal, *, admitted):
        if self._handling.get():
            return DispatchResult("reentrant", "invalid", "invalid", "DENIED", "ORCH_REENTRANT_DENIED")
        token = self._handling.set(True)
        try:
            return self._handle(signal, admitted)
        finally:
            self._handling.reset(token)

    def _handle(self, signal, admitted):
        # Snapshot mutable caller dictionaries before invoking any application port.
        try:
            signal = decode_signal(encode_signal(signal), expected_source=self._source)
        except OrchestrationError as exc:
            return DispatchResult("invalid", "invalid", "invalid", "DENIED", _reason(exc.code))
        refs, ids = (), ()

        def finish(decision, reason, *, degraded=False):
            outcome = DispatchResult(signal.signal_id, signal.kind, signal.task_ref or signal.project_id,
                decision, _reason(reason), ids, refs, ids, (), degraded)
            if self._publisher is not None:
                try:
                    self._publisher(outcome)
                except Exception:
                    outcome = replace(outcome, observability_degraded=True)
            return outcome

        received = self._receiver.handle(signal, admitted=admitted)
        if received.reason != "NOT_APPLICABLE":
            return finish("DENIED", received.reason)
        if signal.kind not in ("ENQUEUE", "REPLAY"):
            return finish("OBSERVED_ONLY", "ORCH_SIGNAL_NOT_DISPATCHABLE")
        if signal.kind != "ENQUEUE" or signal.payload["target"] != "WORKER_BATCH":
            return finish("DENIED", "ORCH_SIGNAL_NOT_DISPATCHABLE")
        try:
            intent = self._authority.read_intent(signal)
            if (type(intent) is not WorkerIntent or intent.task_ref != signal.task_ref
                    or intent.intent_ref != signal.payload["intent_ref"]
                    or intent.project_id != signal.project_id
                    or not all(_ref(v) for v in (intent.task_ref, intent.intent_ref, intent.project_id))):
                return finish("RECONCILIATION_REQUIRED", "ORCH_WORKER_BINDING_INVALID")
            if intent.task_class != "review":
                reason = ("CANONICAL_MUTABLE_CLAIM_AUTHORITY_UNAVAILABLE"
                          if intent.task_class == "mutable" else "ORCH_WORKER_REVIEW_ONLY")
                return finish("DENIED", reason)
            batch = self._authority.read_batch(signal)
            if (type(batch) is not WorkerBatch or type(batch.plan) is not SchedulePlan
                    or type(batch.tasks) is not tuple or len(batch.tasks) != 1
                    or len(batch.plan.selected) != 1
                    or not _ref(batch.ready_generation)
                    or batch.ready_plan_ref != signal.payload["ready_plan_ref"]
                    or batch.task_map_ref != signal.payload["task_map_ref"]
                    or type(batch.evidence_refs) is not tuple or not 1 <= len(batch.evidence_refs) <= 12
                    or not all(_ref(v) for v in batch.evidence_refs)):
                return finish("RECONCILIATION_REQUIRED", "ORCH_WORKER_BINDING_INVALID")
            refs = batch.evidence_refs
            task = batch.tasks[0]
            if (type(task) is not ParallelReadyTask or batch.plan.selected != (task.assignment,)
                    or task.assignment.worker_id != self._worker_id
                    or task.provider_profile.provider_id != self._provider_id
                    or task.lease_request.task_id != intent.task_ref
                    or task.dispatch_request.project_id != intent.project_id
                    or task.lease_request.mutation_intent is not LeaseMutationIntent.READ_ONLY
                    or task.harness_dispatch.mutation_intent is not MutationIntent.READ_ONLY
                    or task.lease_request.mutable_scope):
                return finish("DENIED", "ORCH_WORKER_REVIEW_ONLY")
            if task.provider_profile.max_concurrency != 1:
                return finish("DENIED", "ORCH_WORKER_SERIALIZATION_UNPROVEN")
            job = self._jobs.get_job(task.dispatch_request.key.job_id)
            ids = (job.job_id,)
            if (job.project_id != intent.project_id
                    or signal.work_order_ref != task.dispatch_request.work_order_ref
                    or job.work_order_ref != task.dispatch_request.work_order_ref
                    or job.max_attempts != task.dispatch_request.max_attempts):
                return finish("RECONCILIATION_REQUIRED", "DISPATCH_JOB_IDENTITY_MISMATCH")
            if job.state not in (TaskState.NEW, TaskState.READY) or job.attempt_count != 0:
                decision = ("NO_ACTION" if job.state in (TaskState.VERIFYING, TaskState.REVIEW_PENDING,
                    TaskState.COMPLETE, TaskState.FAILED, TaskState.CANCELLED)
                    else "RECONCILIATION_REQUIRED")
                return finish(decision, "JOB_ALREADY_" + job.state.value)
            facts = batch.utilization_facts
            if (type(facts) is not UtilizationFacts
                    or any(type(getattr(facts, name)) is not int or getattr(facts, name) < 0
                        for name in ("occupied_review_lanes", "occupied_mutable_lanes",
                            "review_lanes_budget", "mutable_lanes_budget"))
                    or facts.review_lanes_budget > 1 or facts.mutable_lanes_budget > 3):
                return finish("RECONCILIATION_REQUIRED", "ORCH_WORKER_AUTHORITY_UNAVAILABLE")
            if facts.occupied_review_lanes >= facts.review_lanes_budget:
                return finish("DENIED", "CAPACITY_EXHAUSTED")
            guards = GuardPipeline(self._authority.check).evaluate(signal,
                utilization_facts=batch.utilization_facts, lane_class="review", scope=intent.scope)
            if not guards.admitted:
                return finish("DENIED", guards.reason)
            executor = self._executor_factory(signal, intent, batch, job)
            if not executor.requires_provider_authority:
                return finish("DENIED", "ORCH_EXECUTOR_REQUIRED")
        except Exception:
            return finish("RECONCILIATION_REQUIRED", "ORCH_WORKER_AUTHORITY_UNAVAILABLE")

        try:
            checkpointed = self._jobs.checkpoint(job.job_id, expected_version=job.version,
                checkpoint_ref="orch-worker-pre:" + job.job_id)
        except Exception:
            return finish("RECONCILIATION_REQUIRED", "ORCH_AUDIT_UNAVAILABLE")
        try:
            # Factory binds the exact post-checkpoint version for final USE.
            executor = self._executor_factory(signal, intent, batch, checkpointed)
            result = executor.execute(batch.plan, {task.assignment.node_id: task},
                provider_inflight={task.provider_profile.provider_id: 0},
                batch_id="orch-worker:" + job.job_id)
            outcome = result.outcomes[0]
            runner_result = outcome.runner_result
            observed = (outcome.kind is ParallelReadyOutcomeKind.RUN_COMPLETED
                and type(runner_result) is GraphDispatchResult
                and runner_result.action is GraphDispatchAction.EXECUTED)
            if type(runner_result) is GraphDispatchResult and runner_result.execution is not None:
                evidence = runner_result.execution.evidence_ref
                if _ref(evidence):
                    refs += (evidence,)
            latest = self._jobs.get_job(job.job_id)
            self._jobs.checkpoint(job.job_id, expected_version=latest.version,
                checkpoint_ref="orch-worker-post:" + job.job_id)
        except Exception:
            return finish("RECONCILIATION_REQUIRED", "ORCH_OUTCOME_RECONCILIATION_REQUIRED", degraded=True)
        return finish("DISPATCH_OBSERVED" if observed else "RECONCILIATION_REQUIRED",
            "ORCH_DISPATCH_OBSERVED" if observed else outcome.reason_code)
