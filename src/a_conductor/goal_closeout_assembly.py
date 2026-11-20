"""WO-P1-409 GOT-1a — production GoalCloseout composition wiring.

REUSE -> WRAP only: this module is a thin composition layer that wires
already-accepted authorities into one production closeout seam. It owns
no second lifecycle, store, scheduler, renderer, task authority, or
continuity authority, and it never parses rendered Markdown as authority.

Reused authorities:
- ``SQLiteJobStore`` (durable job state, CAS transitions, CHECKPOINT
  journal — the journal is the reconstruction source for completed
  closeout stage refs);
- ``SQLiteWorkerLeaseStore`` (lease health + the canonical owner-bound
  release, adapted here to the ``LeaseReleasePort.release(lease_id)``
  protocol while binding session/task/clock identity);
- ``AgentChangeApplier`` + ``ContinuityProjectionFoldAdapter`` (projection
  folds published only through the existing mutation authority);
- ``GoalCloseoutExecutor`` (one durable closeout stage per call).

D1 (integrator decision): a production closeout entry may promote an
existing job from VERIFYING to REVIEW_PENDING only when verification
evidence is identity-bound to the same task and attempt and the
identity-bound verify checkpoint is durably reconstructible from the job
event journal. Missing, stale, or contradictory proof fails closed.

Evidence freshness (attempt-0002): closeout spans multiple durable
calls, so review/merge/ownership/continuity/blocking facts are supplied
by a trusted ``CloseoutEvidenceProvider`` that is re-observed exactly
once at the beginning of each ``next_stage()`` call. The single returned
immutable ``CloseoutEvidenceBundle`` is the one internally-consistent
evidence snapshot bound through that entire stage (promotion decision,
closeout facts, and fold projection); the next ``next_stage()`` call
gets a fresh bundle.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Iterable, Protocol

from .continuity_guard import ContinuityClassification
from .continuity_projection import (
    CANONICAL_TARGETS,
    ContinuityProjectionFoldAdapter,
    ProjectionFacts,
    ProjectionLeaseFact,
)
from .domain import TaskState
from .goal_closeout import (
    CloseoutStage,
    FoldEvidence,
    FoldRequirement,
    GoalCloseoutExecutor,
    GoalCloseoutFacts,
    LeaseEvidence,
    LeaseReleaseOutcome,
    MergeEvidence,
    OwnershipEvidence,
    ReviewEvidence,
    VerificationEvidence,
    closeout_checkpoint_ref,
)
from .job_store import JobEventType, JobStoreError, SQLiteJobStore
from .worker_lease import (
    LeaseHealthKind,
    SQLiteWorkerLeaseStore,
    WorkerLeaseError,
)

_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,64}$")

_STAGE_VERIFYING_PROMOTION = "VERIFYING_PROMOTION"
_STAGE_CLOSEOUT_GATE = "CLOSEOUT_GATE"


class FoldMutationApplierPort(Protocol):
    def apply(self, packet, lease_id: str, **kwargs) -> object: ...


class GoalCloseoutAssemblyError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _text(value: str, field: str, *, max_length: int = 512) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise GoalCloseoutAssemblyError(f"{field.upper()}_INVALID")
    return value.strip()


def _optional_text(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    return _text(value, field)


def _sha(value: str, field: str) -> str:
    text = _text(value, field, max_length=64)
    if not _SHA_RE.fullmatch(text):
        raise GoalCloseoutAssemblyError(f"{field.upper()}_INVALID")
    return text.casefold()


def _clock_text(value: object) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise GoalCloseoutAssemblyError("CLOCK_INVALID")
        return (
            value.astimezone(timezone.utc)
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z")
        )
    if not isinstance(value, str) or not value.strip():
        raise GoalCloseoutAssemblyError("CLOCK_INVALID")
    return value.strip()


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class WorkerLeaseReleaseAdapter:
    """Adapts the canonical ``SQLiteWorkerLeaseStore.release`` signature to
    the ``LeaseReleasePort.release(lease_id)`` protocol while binding the
    existing session/task/clock identity at construction time."""

    def __init__(
        self,
        *,
        store: SQLiteWorkerLeaseStore,
        session_id: str,
        task_id: str,
        clock: Callable[[], object],
    ) -> None:
        if not callable(getattr(store, "release", None)):
            raise GoalCloseoutAssemblyError("LEASE_STORE_INVALID")
        self._store = store
        self._session_id = _text(session_id, "session_id", max_length=128)
        self._task_id = _text(task_id, "task_id", max_length=256)
        if not callable(clock):
            raise GoalCloseoutAssemblyError("CLOCK_INVALID")
        self._clock = clock

    def release(self, lease_id: str) -> LeaseReleaseOutcome:
        result = self._store.release(
            _text(lease_id, "lease_id", max_length=128),
            session_id=self._session_id,
            task_id=self._task_id,
            released_at=self._clock(),
        )
        released = getattr(result, "released", None)
        already = getattr(result, "already_released", None)
        if not isinstance(released, bool) or not isinstance(already, bool):
            raise GoalCloseoutAssemblyError("LEASE_RELEASE_RESULT_INVALID")
        return LeaseReleaseOutcome(released=released, already_released=already)


def completed_closeout_checkpoint_refs(
    job_store: SQLiteJobStore, job_id: str
) -> frozenset[str]:
    """Reconstruct completed closeout stage refs from the durable job event
    journal (CHECKPOINT events only). The journal is the authority; evidence
    claims never substitute for it."""
    _text(job_id, "job_id", max_length=128)
    events = job_store.list_events(job_id)
    return frozenset(
        event.checkpoint_ref
        for event in events
        if event.event_type is JobEventType.CHECKPOINT and event.checkpoint_ref
    )


@dataclass(frozen=True, slots=True)
class CloseoutEvidenceBundle:
    """Identity-bound observed evidence the composition cannot invent.

    Supplied by the caller from durable/observed authorities; never from
    rendered Markdown."""

    verification: VerificationEvidence
    continuity: ContinuityClassification
    review: ReviewEvidence
    merge: MergeEvidence
    fold_requirement: FoldRequirement
    fold_not_required_reason: str | None
    ownership: OwnershipEvidence
    blocking_findings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.verification, VerificationEvidence):
            raise GoalCloseoutAssemblyError("EVIDENCE_VERIFICATION_INVALID")
        if not isinstance(self.continuity, ContinuityClassification):
            raise GoalCloseoutAssemblyError("EVIDENCE_CONTINUITY_INVALID")
        if not isinstance(self.review, ReviewEvidence):
            raise GoalCloseoutAssemblyError("EVIDENCE_REVIEW_INVALID")
        if not isinstance(self.merge, MergeEvidence):
            raise GoalCloseoutAssemblyError("EVIDENCE_MERGE_INVALID")
        if not isinstance(self.fold_requirement, FoldRequirement):
            raise GoalCloseoutAssemblyError("EVIDENCE_FOLD_REQUIREMENT_INVALID")
        if not isinstance(self.ownership, OwnershipEvidence):
            raise GoalCloseoutAssemblyError("EVIDENCE_OWNERSHIP_INVALID")
        reason = self.fold_not_required_reason
        if reason is not None and (
            not isinstance(reason, str) or not reason.strip() or len(reason) > 256
        ):
            raise GoalCloseoutAssemblyError("EVIDENCE_FOLD_REASON_INVALID")
        findings = tuple(self.blocking_findings)
        if any(not isinstance(item, str) or not item.strip() for item in findings):
            raise GoalCloseoutAssemblyError("EVIDENCE_BLOCKING_FINDINGS_INVALID")
        object.__setattr__(self, "blocking_findings", findings)


@dataclass(frozen=True, slots=True)
class ProductionCloseoutResult:
    stage: str
    decision: str
    detail: str = ""


class CloseoutEvidenceProvider(Protocol):
    """Trusted per-stage closeout evidence source.

    The production contract: called exactly once at the beginning of
    each ``next_stage()``; must return one immutable, internally
    consistent :class:`CloseoutEvidenceBundle` re-observed from
    durable/observed authorities for THAT stage. A raise propagates as
    a trusted-source failure; a non-bundle return fails closed typed."""

    def evidence(self) -> CloseoutEvidenceBundle: ...


class StaticCloseoutEvidenceProvider:
    """Deterministic provider returning one immutable, fully
    pre-observed bundle for every stage (bounded lanes/tests)."""

    def __init__(self, bundle: CloseoutEvidenceBundle) -> None:
        if not isinstance(bundle, CloseoutEvidenceBundle):
            raise GoalCloseoutAssemblyError("EVIDENCE_BUNDLE_INVALID")
        self._bundle = bundle

    def evidence(self) -> CloseoutEvidenceBundle:
        return self._bundle


def _closeout_status(state: TaskState) -> str:
    if state is TaskState.COMPLETE:
        return "COMPLETE"
    if state is TaskState.RECOVERY_NEEDED:
        return "RECOVERY_REQUIRED"
    if state in (TaskState.BLOCKED, TaskState.FAILED, TaskState.CANCELLED):
        return "BLOCKED"
    return "FOLD_PENDING"


def _post_main_status(merge: MergeEvidence) -> str:
    if not merge.post_main_required:
        return "NOT_REQUIRED"
    if merge.post_main_success is True:
        return "SUCCESS"
    if merge.post_main_success is False:
        return "FAILED"
    return "PENDING" if merge.post_main_run_id else "UNKNOWN"


def _projection_lease_fact(
    lease, *, now_text: str, session_id: str, task_id: str
) -> ProjectionLeaseFact:
    state = "UNKNOWN"
    if getattr(lease, "quarantine_code", None) is not None:
        state = "QUARANTINED"
    else:
        expires_at = getattr(lease, "expires_at", None)
        if isinstance(expires_at, str) and expires_at.strip():
            try:
                state = (
                    "STALE"
                    if _parse_timestamp(now_text) >= _parse_timestamp(expires_at)
                    else "ACTIVE"
                )
            except ValueError:
                state = "UNKNOWN"
    return ProjectionLeaseFact(
        lease_id=lease.lease_id,
        session_id=lease.session_id,
        task_id=lease.task_id,
        state=state,
        owner_ok=(lease.session_id == session_id and lease.task_id == task_id),
    )


_LEASE_STATE_BY_HEALTH: dict[LeaseHealthKind, str] = {
    LeaseHealthKind.ACTIVE: "ACTIVE",
    LeaseHealthKind.RELEASED: "RELEASED",
    LeaseHealthKind.QUARANTINED: "QUARANTINED",
    LeaseHealthKind.STALE: "STALE",
    LeaseHealthKind.EXPIRY_UNKNOWN: "UNKNOWN",
}


class ProductionGoalCloseoutFacade:
    """Bounded production closeout facade.

    Performs AT MOST ONE durable closeout stage per ``next_stage`` call:
    either the D1 VERIFYING->REVIEW_PENDING promotion, one delegated
    GoalCloseoutExecutor stage (verify checkpoint / fold / lease release /
    COMPLETE), or a typed fail-closed result with zero durable writes."""

    def __init__(
        self,
        *,
        job_store: SQLiteJobStore,
        lease_store: SQLiteWorkerLeaseStore,
        executor: GoalCloseoutExecutor | None = None,
        evidence_provider: CloseoutEvidenceProvider,
        job_id: str,
        task_id: str,
        attempt_id: str,
        session_id: str,
        lease_id: str | None,
        candidate_sha: str,
        branch: str,
        actual_head: str,
        clock: Callable[[], object],
    ) -> None:
        if executor is not None and not isinstance(executor, GoalCloseoutExecutor):
            raise GoalCloseoutAssemblyError("EXECUTOR_INVALID")
        if not callable(getattr(evidence_provider, "evidence", None)):
            raise GoalCloseoutAssemblyError("EVIDENCE_PROVIDER_INVALID")
        self._executor = executor
        self._job_store = job_store
        self._lease_store = lease_store
        self._evidence_provider = evidence_provider
        self._stage_evidence: CloseoutEvidenceBundle | None = None
        self._job_id = _text(job_id, "job_id", max_length=128)
        self._task_id = _text(task_id, "task_id", max_length=256)
        self._attempt_id = _text(attempt_id, "attempt_id", max_length=256)
        self._session_id = _text(session_id, "session_id", max_length=128)
        self._lease_id = _optional_text(lease_id, "lease_id")
        if self._lease_id is not None:
            self._lease_id = _text(self._lease_id, "lease_id", max_length=128)
        self._candidate_sha = _sha(candidate_sha, "candidate_sha")
        self._branch = _text(branch, "branch", max_length=256)
        self._actual_head = _sha(actual_head, "actual_head")
        if not callable(clock):
            raise GoalCloseoutAssemblyError("CLOCK_INVALID")
        self._clock = clock
        self._verify_ref = closeout_checkpoint_ref(
            CloseoutStage.VERIFY_CHECKPOINT,
            task_id=self._task_id,
            candidate_sha=self._candidate_sha,
            attempt_id=self._attempt_id,
        )

    def next_stage(self, job_id: str) -> ProductionCloseoutResult:
        if self._executor is None:
            raise GoalCloseoutAssemblyError("EXECUTOR_NOT_CONFIGURED")
        requested = _text(job_id, "job_id", max_length=128)
        if requested != self._job_id:
            raise GoalCloseoutAssemblyError("CLOSEOUT_JOB_MISMATCH")
        bundle = self._begin_stage()
        try:
            job = self._job_store.get_job(self._job_id)
            if job.state is TaskState.COMPLETE:
                return ProductionCloseoutResult(
                    CloseoutStage.DONE.value, "ALREADY_COMPLETE"
                )
            if job.state in (TaskState.FAILED, TaskState.CANCELLED):
                return ProductionCloseoutResult(
                    CloseoutStage.DONE.value, "REFUSED", job.state.value
                )
            if job.state is TaskState.VERIFYING:
                return self._promotion_stage(job, bundle)
            if job.state is TaskState.REVIEW_PENDING:
                return self._executor_stage(job, bundle)
            return ProductionCloseoutResult(
                _STAGE_CLOSEOUT_GATE, "CLOSEOUT_STATE_INVALID", job.state.value
            )
        finally:
            self._end_stage()

    def _begin_stage(self) -> CloseoutEvidenceBundle:
        """Re-observe trusted evidence exactly once for this stage; the
        returned immutable bundle is the single snapshot bound through
        the whole stage."""
        bundle = self._evidence_provider.evidence()
        if not isinstance(bundle, CloseoutEvidenceBundle):
            raise GoalCloseoutAssemblyError("EVIDENCE_BUNDLE_INVALID")
        self._stage_evidence = bundle
        return bundle

    def _end_stage(self) -> None:
        self._stage_evidence = None

    def _stage_bundle(self) -> CloseoutEvidenceBundle:
        bundle = self._stage_evidence
        if bundle is None:
            raise GoalCloseoutAssemblyError("EVIDENCE_STAGE_NOT_ACTIVE")
        return bundle

    def _promotion_stage(self, job, bundle: CloseoutEvidenceBundle) -> ProductionCloseoutResult:
        evidence = bundle.verification
        if not evidence.ok:
            return ProductionCloseoutResult(
                _STAGE_VERIFYING_PROMOTION, "BLOCK", "VERIFY_EVIDENCE_MISSING"
            )
        if evidence.task_id != self._task_id or evidence.attempt_id != self._attempt_id:
            return ProductionCloseoutResult(
                _STAGE_VERIFYING_PROMOTION, "BLOCK", "VERIFY_IDENTITY_MISMATCH"
            )
        if (
            evidence.mutation_version is not None
            and evidence.checkpoint_version is not None
            and evidence.mutation_version > evidence.checkpoint_version
        ):
            return ProductionCloseoutResult(
                _STAGE_VERIFYING_PROMOTION,
                "RECOVERY_REQUIRED",
                "MUTATION_AHEAD_OF_JOURNAL",
            )
        refs = completed_closeout_checkpoint_refs(self._job_store, self._job_id)
        if self._verify_ref not in refs:
            result = self._executor.execute_next(self._build_facts(job, refs, bundle))
            return ProductionCloseoutResult(
                result.stage.value, result.decision.value, result.detail
            )
        try:
            self._job_store.transition(
                self._job_id,
                TaskState.REVIEW_PENDING,
                expected_version=job.version,
                evidence_ref=self._verify_ref,
            )
        except JobStoreError as exc:
            if exc.code == "JOB_VERSION_CONFLICT":
                return ProductionCloseoutResult(
                    _STAGE_VERIFYING_PROMOTION, "RELOAD_REPLAN", "JOB_VERSION_CONFLICT"
                )
            raise
        return ProductionCloseoutResult(
            _STAGE_VERIFYING_PROMOTION, "PROMOTED_TO_REVIEW_PENDING", self._verify_ref
        )

    def _executor_stage(
        self, job, bundle: CloseoutEvidenceBundle
    ) -> ProductionCloseoutResult:
        refs = completed_closeout_checkpoint_refs(self._job_store, self._job_id)
        result = self._executor.execute_next(self._build_facts(job, refs, bundle))
        return ProductionCloseoutResult(
            result.stage.value, result.decision.value, result.detail
        )

    def _build_facts(
        self, job, refs: frozenset[str], bundle: CloseoutEvidenceBundle
    ) -> GoalCloseoutFacts:
        evidence = bundle
        raw_verification = evidence.verification
        checkpoint_version = raw_verification.checkpoint_version
        if self._verify_ref in refs and checkpoint_version is None:
            checkpoint_version = job.version
        verification = VerificationEvidence(
            task_id=raw_verification.task_id,
            attempt_id=raw_verification.attempt_id,
            ok=raw_verification.ok,
            checkpoint_ref=raw_verification.checkpoint_ref,
            mutation_version=raw_verification.mutation_version,
            checkpoint_version=checkpoint_version,
        )
        merge = evidence.merge
        merge_key = merge.merge_commit if merge.required else "nomerge"
        fold_ref = (
            closeout_checkpoint_ref(
                CloseoutStage.FOLD,
                task_id=self._task_id,
                candidate_sha=self._candidate_sha,
                merge_key=merge_key,
                fold_key="required",
            )
            if merge_key
            else None
        )
        fold_done = fold_ref is not None and fold_ref in refs
        fold = FoldEvidence(
            requirement=evidence.fold_requirement,
            not_required_reason=evidence.fold_not_required_reason,
            completed=True if fold_done else None,
            bound_task_id=self._task_id if fold_done else None,
            bound_merge_commit=merge.merge_commit if fold_done else None,
        )
        return GoalCloseoutFacts(
            job_id=job.job_id,
            task_id=self._task_id,
            attempt_id=self._attempt_id,
            state=job.state,
            version=job.version,
            verification=verification,
            blocking_findings=tuple(evidence.blocking_findings),
            continuity=evidence.continuity,
            current_candidate_sha=self._candidate_sha,
            review=evidence.review,
            merge=merge,
            fold=fold,
            lease=self._lease_evidence(),
            ownership=evidence.ownership,
            completed_closeout_refs=refs,
        )

    def _lease_evidence(self) -> LeaseEvidence:
        if self._lease_id is None:
            return LeaseEvidence(lease_id=None, state=None, owner_ok=True)
        try:
            health = self._lease_store.inspect_health(self._lease_id, now=self._clock())
        except WorkerLeaseError:
            return LeaseEvidence(
                lease_id=self._lease_id, state="UNKNOWN", owner_ok=True
            )
        lease = health.lease
        state = _LEASE_STATE_BY_HEALTH.get(health.kind, "UNKNOWN")
        owner_ok = (
            lease.session_id == self._session_id and lease.task_id == self._task_id
        )
        return LeaseEvidence(lease_id=self._lease_id, state=state, owner_ok=owner_ok)

    def _projection_facts(self) -> ProjectionFacts:
        evidence = self._stage_bundle()
        job = self._job_store.get_job(self._job_id)
        now_text = _clock_text(self._clock())
        leases = tuple(
            _projection_lease_fact(
                lease,
                now_text=now_text,
                session_id=self._session_id,
                task_id=self._task_id,
            )
            for lease in self._lease_store.list_active()
        )
        return ProjectionFacts(
            task_id=self._task_id,
            candidate_sha=self._candidate_sha,
            branch=self._branch,
            head=self._actual_head,
            merge_commit=evidence.merge.merge_commit,
            post_main_status=_post_main_status(evidence.merge),
            closeout_status=_closeout_status(job.state),
            leases=leases,
            ownership_known=evidence.ownership.known,
            writer_session=self._session_id,
        )


def assemble_goal_closeout_facade(
    *,
    job_store: SQLiteJobStore,
    lease_store: SQLiteWorkerLeaseStore,
    applier: FoldMutationApplierPort,
    evidence_provider: CloseoutEvidenceProvider,
    job_id: str,
    task_id: str,
    attempt_id: str,
    session_id: str,
    lease_id: str | None,
    candidate_sha: str,
    branch: str,
    actual_head: str,
    clock: Callable[[], object],
    targets: Iterable[str] = CANONICAL_TARGETS,
) -> ProductionGoalCloseoutFacade:
    """Assemble the production closeout composition from existing
    authorities only: job store journal, canonical lease store release,
    AgentChangeApplier-gated projection fold, and the GoalCloseout
    executor. The trusted evidence provider is re-observed exactly once
    per ``next_stage()`` call."""
    for method in ("get_job", "transition", "checkpoint", "list_events"):
        if not callable(getattr(job_store, method, None)):
            raise GoalCloseoutAssemblyError("JOB_STORE_INVALID")
    for method in ("release", "inspect_health", "list_active"):
        if not callable(getattr(lease_store, method, None)):
            raise GoalCloseoutAssemblyError("LEASE_STORE_INVALID")
    if not callable(getattr(evidence_provider, "evidence", None)):
        raise GoalCloseoutAssemblyError("EVIDENCE_PROVIDER_INVALID")
    if not callable(getattr(applier, "apply", None)):
        raise GoalCloseoutAssemblyError("APPLIER_INVALID")
    if not callable(clock):
        raise GoalCloseoutAssemblyError("CLOCK_INVALID")
    facade = ProductionGoalCloseoutFacade(
        job_store=job_store,
        lease_store=lease_store,
        executor=None,
        evidence_provider=evidence_provider,
        job_id=job_id,
        task_id=task_id,
        attempt_id=attempt_id,
        session_id=session_id,
        lease_id=lease_id,
        candidate_sha=candidate_sha,
        branch=branch,
        actual_head=actual_head,
        clock=clock,
    )
    release_port = WorkerLeaseReleaseAdapter(
        store=lease_store,
        session_id=facade._session_id,
        task_id=facade._task_id,
        clock=clock,
    )
    fold_port = ContinuityProjectionFoldAdapter(
        applier=applier,
        lease_id=facade._lease_id or "no-mutation-lease",
        session_id=facade._session_id,
        task_id=facade._task_id,
        actual_head=facade._actual_head,
        facts_factory=facade._projection_facts,
        targets=targets,
    )
    facade._executor = GoalCloseoutExecutor(
        job_store=job_store,
        lease_release_port=release_port,
        fold_port=fold_port,
    )
    return facade


@dataclass(frozen=True, slots=True)
class GoalCloseoutCompositionConfig:
    """Bounded production closeout composition input for
    ``DurableJobControlService.open()``.

    ``compose`` assembles the closeout facade from the SAME
    ``SQLiteJobStore`` the service opens — no second store, database, or
    lifecycle. The trusted evidence provider is re-observed once per
    closeout stage; everything else is existing authority."""

    evidence_provider: CloseoutEvidenceProvider
    applier: FoldMutationApplierPort
    lease_store: SQLiteWorkerLeaseStore
    job_id: str
    task_id: str
    attempt_id: str
    session_id: str
    lease_id: str | None
    candidate_sha: str
    branch: str
    actual_head: str
    clock: Callable[[], object]
    targets: tuple[str, ...] = CANONICAL_TARGETS

    def __post_init__(self) -> None:
        if not callable(getattr(self.evidence_provider, "evidence", None)):
            raise GoalCloseoutAssemblyError("EVIDENCE_PROVIDER_INVALID")
        if not callable(getattr(self.applier, "apply", None)):
            raise GoalCloseoutAssemblyError("APPLIER_INVALID")
        for method in ("release", "inspect_health", "list_active"):
            if not callable(getattr(self.lease_store, method, None)):
                raise GoalCloseoutAssemblyError("LEASE_STORE_INVALID")
        if not callable(self.clock):
            raise GoalCloseoutAssemblyError("CLOCK_INVALID")
        object.__setattr__(self, "targets", tuple(self.targets))

    def compose(self, *, job_store: SQLiteJobStore) -> ProductionGoalCloseoutFacade:
        return assemble_goal_closeout_facade(
            job_store=job_store,
            lease_store=self.lease_store,
            applier=self.applier,
            evidence_provider=self.evidence_provider,
            job_id=self.job_id,
            task_id=self.task_id,
            attempt_id=self.attempt_id,
            session_id=self.session_id,
            lease_id=self.lease_id,
            candidate_sha=self.candidate_sha,
            branch=self.branch,
            actual_head=self.actual_head,
            clock=self.clock,
            targets=self.targets,
        )
