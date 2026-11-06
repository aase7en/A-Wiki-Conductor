"""Unwired Parent inspection and existing-job audit seams for WO-P1-733.

No public operator action, credential implementation, queue writer or serialization
authority is registered here. Application ports are trusted dependencies, never
external PASS receipts. Live registration and all-producer ordering are later gates.
"""
from __future__ import annotations

from dataclasses import dataclass

from .a_faster_utilization_guard import UtilizationFacts
from .codex_queue_submission_guard import TASK_KEY_PREFIX
from .domain import TaskState
from .job_state import JobRuntimeState
from .job_store import JobEvent, JobEventType
from .orchestration import (
    OrchestrationError, OrchestrationOutcome, OrchestrationSignal,
    decode_signal, encode_outcome, encode_signal,
)
from .orchestration_dispatcher import DispatchResult
from .orchestration_guards import AuthorityGuard, DuplicateGuard, GuardPipeline, UtilizationGuard
from .orchestration_receiver import AdmittedContext, SignalReceiver


def _ref(value, limit=256):
    return (type(value) is str and 1 <= len(value) <= limit
            and all(33 <= ord(c) <= 126 for c in value))


def _intent_valid(value):
    return (type(value) is ParentIntent
        and all(_ref(getattr(value, name), 128) for name in (
            "project_id", "task_ref", "work_order_ref", "intent_ref"))
        and all(_ref(getattr(value, name)) for name in (
            "repository_ref", "parent_binding_ref", "evidence_ref"))
        and type(value.aliases) is tuple and 1 <= len(value.aliases) <= 32
        and all(_ref(alias) for alias in value.aliases)
        and len(set(value.aliases)) == len(value.aliases)
        and type(value.scope) is tuple and 1 <= len(value.scope) <= 64
        and all(_ref(item) for item in value.scope)
        and len(set(value.scope)) == len(value.scope)
        and (value.job_id is None or _ref(value.job_id))
        and (value.job_version is None or
             (type(value.job_version) is int and value.job_version >= 1)))


@dataclass(frozen=True, slots=True)
class ParentRequest:
    signal_id: str
    kind: str
    occurred_at: str
    repository_ref: str
    project_id: str
    task_alias: str
    intent_ref: str
    prior_submission_ref: str | None = None
    recovery_evidence_ref: str | None = None
    trigger: str = "EXPLICIT"


@dataclass(frozen=True, slots=True)
class ParentCredential:
    """Only the bound Sunday verifier supplies this projection, not the caller."""
    issuer_ref: str
    caller_ref: str
    device_id: str
    repository_ref: str
    project_id: str


@dataclass(frozen=True, slots=True)
class ParentIntent:
    """One task/intent and its aliases proven by the durable coordination owner.

    job_id is resolved by this owner, never taken from a caller-selected job.
    evidence_ref must resolve to the existing canonical intent/job binding.
    """
    repository_ref: str
    project_id: str
    task_ref: str
    work_order_ref: str
    intent_ref: str
    parent_binding_ref: str
    aliases: tuple[str, ...]
    job_id: str | None
    job_version: int | None
    evidence_ref: str
    scope: tuple[str, ...]
    utilization_facts: UtilizationFacts | None = None
    lane_class: str | None = None


@dataclass(frozen=True, slots=True)
class ParentRecovery:
    """Existing recovery owner's exact task/result linkage, not turn status."""
    task_ref: str
    intent_ref: str
    parent_binding_ref: str
    thread_id: str
    submission_id: str
    evidence_ref: str
    state: str


class ParentAudit:
    """Thin adapter over the existing job owner, not an enqueue capability.

    checkpoint_before/record_observed are deliberately NOT called by inspection.
    A future admitted writer must own serialization around the entire operation;
    job checkpoint CAS does not serialize an external queue.
    """
    def __init__(self, jobs):
        self._jobs = jobs

    def _job(self, intent, expected_version):
        if not _intent_valid(intent) or intent.job_id is None:
            raise OrchestrationError("ORCH_PARENT_AUDIT_OWNER_REQUIRED")
        try:
            job = self._jobs.get_job(intent.job_id)
        except Exception:
            raise OrchestrationError("ORCH_PARENT_AUDIT_OWNER_REQUIRED") from None
        if (type(job) is not JobRuntimeState or job.job_id != intent.job_id
                or job.project_id != intent.project_id
                or job.work_order_ref != intent.work_order_ref
                or job.state not in (TaskState.NEW, TaskState.READY)
                or job.worker_id is not None or job.attempt_count != 0):
            raise OrchestrationError("ORCH_PARENT_AUDIT_OWNER_REQUIRED")
        if (type(expected_version) is not int or type(job.version) is not int
                or job.version != expected_version):
            raise OrchestrationError("JOB_VERSION_CONFLICT")
        return job

    def _events(self, intent):
        try:
            events = self._jobs.list_events(intent.job_id)
            if (type(events) is not tuple or not events
                    or any(type(e) is not JobEvent or e.job_id != intent.job_id
                        or type(e.sequence_no) is not int or e.sequence_no != i
                        or type(e.event_type) is not JobEventType
                        or (e.checkpoint_ref is not None and not _ref(e.checkpoint_ref))
                        for i, e in enumerate(events, 1))):
                raise ValueError
            return events
        except Exception:
            raise OrchestrationError("ORCH_AUDIT_UNAVAILABLE") from None

    def inspect(self, intent, *, reconciliation_only=False):
        job = self._job(intent, intent.job_version)
        events = self._events(intent)
        # Even a matched post is a prior submission, never fresh-intent permission.
        if not reconciliation_only and any(e.checkpoint_ref is not None and e.checkpoint_ref.startswith(
                ("orch-parent-pre:", "orch-parent-post:")) for e in events):
            raise OrchestrationError("ORCH_PARENT_PRIOR_SUBMISSION_UNRESOLVED")
        if self._job(intent, job.version) != job:
            raise OrchestrationError("JOB_VERSION_CONFLICT")
        return job

    def checkpoint_before(self, intent, signal_id):
        if not _ref(signal_id, 128):
            raise OrchestrationError("SIGNAL_VALUE_INVALID")
        job = self.inspect(intent)
        try:
            checkpointed = self._jobs.checkpoint(job.job_id, expected_version=job.version,
                checkpoint_ref="orch-parent-pre:" + signal_id,
                evidence_ref=intent.evidence_ref)
            if (type(checkpointed) is not JobRuntimeState
                    or checkpointed != self._job(intent, job.version + 1)):
                raise ValueError
            return checkpointed
        except Exception:
            raise OrchestrationError("ORCH_AUDIT_UNAVAILABLE") from None

    def record_observed(self, intent, signal_id, *, expected_version,
                        submission_ref, evidence_ref):
        # Validate caller-visible identifiers before retaining observed evidence.
        outcome = OrchestrationOutcome(signal_id, "ENQUEUE", "SUBMISSION_OBSERVED",
            "ORCH_SUBMISSION_OBSERVED", (evidence_ref,), submission_ref=submission_ref)
        encode_outcome(outcome)
        try:
            self._job(intent, expected_version)
            events = self._events(intent)
            pre = events[-1]
            if (pre.event_type is not JobEventType.CHECKPOINT
                    or pre.checkpoint_ref != "orch-parent-pre:" + signal_id
                    or pre.evidence_ref != intent.evidence_ref):
                raise ValueError
            checkpointed = self._jobs.checkpoint(intent.job_id, expected_version=expected_version,
                checkpoint_ref="orch-parent-post:" + signal_id, evidence_ref=evidence_ref)
            if (type(checkpointed) is not JobRuntimeState
                    or checkpointed != self._job(intent, expected_version + 1)):
                raise ValueError
        except Exception:
            return OrchestrationOutcome(signal_id, "ENQUEUE", "RECONCILIATION_REQUIRED",
                "ORCH_OUTCOME_RECONCILIATION_REQUIRED", (evidence_ref,),
                submission_ref=submission_ref, observability_degraded=True)
        return outcome


class ParentAdmission:
    """Read-only application seam; successful preflight NEVER authorizes a write.

    verifier must authenticate the raw credential using the accepted Sunday issuer
    boundary, including validity/revocation/PoP as that boundary requires. This
    class only checks its typed identity projection. There is no shipped verifier
    binding here, nor a public request/credential-to-operator mapping.
    resolve_intent must read the current durable owner, not parse aliases or accept
    an external admission receipt. resolve_recovery similarly owns result linkage.
    """
    def __init__(self, *, verifier, expected_issuer, resolve_intent, receiver,
                 authority_checker, audit, resolve_recovery=None):
        self._verifier, self._issuer = verifier, expected_issuer
        self._resolve_intent, self._receiver = resolve_intent, receiver
        self._authority, self._audit = authority_checker, audit
        self._recovery = resolve_recovery
        if (not _ref(expected_issuer) or not callable(resolve_intent)
                or type(receiver) is not SignalReceiver or type(audit) is not ParentAudit
                or (verifier is not None and not callable(verifier))
                or (resolve_recovery is not None and not callable(resolve_recovery))):
            raise ValueError("ORCH_PARENT_CONFIGURATION_INVALID")

    def inspect(self, request, *, credential, caller_ref, device_id):
        signal_id, kind, task_ref, ids = "invalid", "invalid", "invalid", ()

        def finish(reason, decision="RECONCILIATION_REQUIRED", refs=()):
            return DispatchResult(signal_id, kind, task_ref, decision, reason,
                evidence_refs=refs, submission_ids=ids)

        if type(caller_ref) is not str or caller_ref != "operator.v1":
            return finish("ORCH_PARENT_CALLER_DENIED", "DENIED")
        if (type(request) is not ParentRequest or not _ref(device_id)
                or not all(_ref(getattr(request, name)) for name in (
                    "repository_ref", "task_alias", "intent_ref"))
                or not _ref(request.signal_id, 128) or not _ref(request.project_id, 128)
                or type(request.kind) is not str or request.kind not in ("ENQUEUE", "REPLAY")
                or not _ref(request.occurred_at, 40)
                or type(request.trigger) is not str or request.trigger not in ("EXPLICIT", "REFILL")
                or (request.kind == "REPLAY" and not all(_ref(v, 128) for v in (
                    request.prior_submission_ref, request.recovery_evidence_ref)))
                or (request.kind == "ENQUEUE" and any(v is not None for v in (
                    request.prior_submission_ref, request.recovery_evidence_ref)))):
            return finish("SIGNAL_VALUE_INVALID", "DENIED")
        signal_id, kind = request.signal_id, request.kind
        try:
            verified = self._verifier(credential) if self._verifier is not None else None
            if (type(verified) is not ParentCredential
                    or not all(_ref(getattr(verified, name)) for name in (
                        "issuer_ref", "caller_ref", "device_id", "repository_ref", "project_id"))
                    or verified != ParentCredential(self._issuer, "operator.v1", device_id,
                        request.repository_ref, request.project_id)):
                return finish("ORCH_PARENT_CREDENTIAL_DENIED", "DENIED")
        except Exception:
            return finish("ORCH_PARENT_CREDENTIAL_DENIED", "DENIED")
        try:
            intent = self._resolve_intent(request)
            if (not _intent_valid(intent) or intent.repository_ref != request.repository_ref
                    or intent.project_id != request.project_id or intent.intent_ref != request.intent_ref
                    or request.task_alias not in (intent.task_ref, *intent.aliases)):
                return finish("ORCH_PARENT_IDENTITY_UNRESOLVED")
        except Exception:
            return finish("ORCH_PARENT_IDENTITY_UNRESOLVED")
        task_ref = intent.task_ref
        payload = {"target": "PARENT_QUEUE", "intent_ref": intent.intent_ref,
            "parent_binding_ref": intent.parent_binding_ref, "trigger": request.trigger}
        if kind == "REPLAY":
            payload.update(prior_submission_ref=request.prior_submission_ref,
                recovery_evidence_ref=request.recovery_evidence_ref)
        try:
            signal = decode_signal(encode_signal(OrchestrationSignal("orch-signal.v1",
                signal_id, kind, request.occurred_at, "operator.v1", intent.project_id,
                payload, task_ref, intent.work_order_ref)))
        except OrchestrationError as exc:
            return finish(exc.code, "DENIED")
        received = self._receiver.handle(signal,
            admitted=AdmittedContext("operator.v1", intent.project_id, task_ref))
        duplicate = DuplicateGuard().evaluate(signal, evidence=received.evidence)
        ids = duplicate.metadata.get("duplicate_submission_ids", ())
        if len(ids) > 16:
            ids = ()
            return finish("EVIDENCE_OVERFLOW")
        # Preserve #583's positive duplicate precedence even on partial collection.
        if ids and kind == "ENQUEUE":
            return finish("QUEUE_GUARD_DUPLICATE_PENDING", "DENIED")
        if not received.admitted:
            return finish(received.reason)
        if not duplicate.admitted and not ids:
            return finish(duplicate.metadata.get("reason_code", "RECONCILIATION_REQUIRED"))
        if any(t.status == "interrupted" for t in received.evidence["turns"]):
            return finish("QUEUE_GUARD_TURN_INTERRUPTED")
        if any(t.status == "inProgress" for t in received.evidence["turns"]):
            return finish("ORCH_PARENT_TURN_ACTIVE")
        if any(not q.client_user_message_id.startswith(TASK_KEY_PREFIX)
                for q in received.evidence["queue_entries"]):
            return finish("ORCH_PARENT_IDENTITY_UNRESOLVED")
        if ids:
            # REPLAY may attach a duplicate, but never turn that into guard PASS.
            for guard in (UtilizationGuard(), AuthorityGuard(self._authority)):
                verdict = guard.evaluate(signal, utilization_facts=intent.utilization_facts,
                    lane_class=intent.lane_class, scope=intent.scope)
                if not verdict.admitted and verdict.reason != "NOT_APPLICABLE":
                    return finish(verdict.reason, "DENIED")
        else:
            verdict = GuardPipeline(self._authority).evaluate(signal, evidence=received.evidence,
                utilization_facts=intent.utilization_facts, lane_class=intent.lane_class,
                scope=intent.scope)
            if not verdict.admitted:
                return finish(verdict.reason, "DENIED")
        try:
            # Reading existing effect evidence may attach a result, but never
            # clears the durable pre-checkpoint or enables a fresh append.
            self._audit.inspect(intent, reconciliation_only=kind == "REPLAY")
        except OrchestrationError as exc:
            return finish(exc.code, "DENIED" if exc.code == "ORCH_PARENT_AUDIT_OWNER_REQUIRED"
                else "RECONCILIATION_REQUIRED")
        except Exception:
            return finish("ORCH_AUDIT_UNAVAILABLE")
        proof = None
        if kind == "REPLAY":
            try:
                proof = self._recovery(intent, request.prior_submission_ref,
                    request.recovery_evidence_ref) if self._recovery is not None else None
                if (type(proof) is not ParentRecovery
                        or not all(_ref(getattr(proof, name)) for name in (
                            "task_ref", "intent_ref", "parent_binding_ref", "thread_id",
                            "submission_id", "evidence_ref"))
                        or (proof.task_ref, proof.intent_ref, proof.parent_binding_ref,
                            proof.thread_id, proof.submission_id, proof.evidence_ref) != (
                            task_ref, intent.intent_ref, intent.parent_binding_ref, received.thread_id,
                            request.prior_submission_ref, request.recovery_evidence_ref)
                        or type(proof.state) is not str or proof.state not in ("PENDING", "TERMINAL")
                        or (proof.state == "PENDING" and ids != (proof.submission_id,))
                        or (proof.state == "TERMINAL" and ids)):
                    return finish("ORCH_PARENT_RECOVERY_UNRESOLVED")
            except Exception:
                return finish("ORCH_PARENT_RECOVERY_UNRESOLVED")
        try:
            current = self._resolve_intent(request)
            if not _intent_valid(current) or current != intent:
                return finish("ORCH_PARENT_BINDING_DRIFT")
            self._audit.inspect(intent, reconciliation_only=kind == "REPLAY")
        except OrchestrationError as exc:
            return finish(exc.code)
        except Exception:
            return finish("ORCH_PARENT_BINDING_DRIFT")
        if proof is not None:
            ids = (proof.submission_id,)
            return finish("ORCH_PARENT_RESULT_ATTACHED", "NO_ACTION", (proof.evidence_ref,))
        return finish("ORCH_QUEUE_SERIALIZATION_UNPROVEN", "DENIED")
