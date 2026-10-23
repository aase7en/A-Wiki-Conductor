"""Pure preflight composition; results never replace final dispatch authority.

The receiver owns authenticated ingress and fresh, task-bound evidence. This
module owns no readers, effects, leases, retry state or serialization. In
particular, #583 is not a worker deduper and #517 is not launch authority.
"""

from dataclasses import dataclass, field, fields
from typing import Callable

from .a_faster_utilization_guard import (
    AFasterActivation, DEFAULT_MUTABLE_LANES, DEFAULT_REVIEW_LANES,
    QuotaAdmission, UtilizationFacts, classify_utilization,
)
from .codex_queue_submission_guard import (
    GuardAction, QueueSubmissionGuardError, evaluate_bootstrap_guard,
)
from .orchestration import OrchestrationError, OrchestrationSignal, encode_signal


@dataclass(frozen=True, slots=True)
class GuardResult:
    admitted: bool
    reason: str
    metadata: dict = field(default_factory=dict)


def _invalid_signal(signal: OrchestrationSignal) -> GuardResult | None:
    try:
        encode_signal(signal)
    except OrchestrationError as exc:
        return GuardResult(False, exc.code)
    return None


class DuplicateGuard:
    """Wrap #583 unchanged for Parent intents, never infer missing evidence."""

    def evaluate(self, signal: OrchestrationSignal, *, evidence: dict | None = None,
                 **_unused) -> GuardResult:
        invalid = _invalid_signal(signal)
        if invalid is not None:
            return invalid
        if signal.signal_type not in ("enqueue", "replay"):
            return GuardResult(False, "NOT_APPLICABLE")
        if signal.payload["target"] != "PARENT_QUEUE":
            return GuardResult(False, "RECONCILIATION_REQUIRED",
                               {"reason_code": "WORKER_DEDUP_AUTHORITY_REQUIRED"})
        required = {"queue_entries", "turns", "queue_evidence_complete", "turn_evidence_complete"}
        diagnostic = {"queue_pages", "turn_binding"}
        optional = {"queue_next_cursor", "turn_next_cursor"} | diagnostic
        if (type(evidence) is not dict or required - evidence.keys()
                or evidence.keys() - (required | optional)):
            return GuardResult(False, "RECONCILIATION_REQUIRED")
        try:
            decision = evaluate_bootstrap_guard(
                signal.task_ref, **{key: value for key, value in evidence.items() if key not in diagnostic})
        except QueueSubmissionGuardError as exc:
            return GuardResult(False, "RECONCILIATION_REQUIRED", {"reason_code": str(exc)})
        return GuardResult(
            decision.action is GuardAction.PROCEED,
            "PASS" if decision.action is GuardAction.PROCEED else decision.action.value,
            {"reason_code": decision.reason_code,
             "duplicate_submission_ids": decision.duplicate_submission_ids,
             "interrupted_turn_ids": decision.interrupted_turn_ids},
        )


class UtilizationGuard:
    """Wrap #517 only for refill; a positive obligation remains advisory."""

    def evaluate(self, signal: OrchestrationSignal, *,
                 utilization_facts: UtilizationFacts | None = None,
                 lane_class: str | None = None, **_unused) -> GuardResult:
        invalid = _invalid_signal(signal)
        if invalid is not None:
            return invalid
        if (signal.signal_type not in ("enqueue", "replay")
                or signal.payload["trigger"] != "REFILL"):
            return GuardResult(False, "NOT_APPLICABLE")
        facts = utilization_facts
        if (type(facts) is not UtilizationFacts or (lane_class is not None
                and (type(lane_class) is not str or lane_class not in ("mutable", "review")))):
            return GuardResult(False, "RECONCILIATION_REQUIRED")
        # Dataclass annotations do not validate enum/bool fields. Reconstruct
        # validated counts too: even frozen instances can arrive corrupted.
        if (type(facts.activation) is not AFasterActivation
                or type(facts.glm_quota_admission) is not QuotaAdmission
                or any(type(getattr(facts, name)) is not bool for name in (
                    "glm_route_ready", "sol_direct_long_labor_active", "sol_direct_labor_glm_eligible"))
                or any(type(getattr(facts, name)) is not int for name in (
                    "occupied_mutable_lanes", "occupied_review_lanes", "ready_mutable_candidates",
                    "ready_review_candidates", "mutable_lanes_budget", "review_lanes_budget"))):
            return GuardResult(False, "RECONCILIATION_REQUIRED")
        try:
            facts = UtilizationFacts(**{item.name: getattr(facts, item.name) for item in fields(facts)})
        except ValueError:
            return GuardResult(False, "RECONCILIATION_REQUIRED")
        if (facts.mutable_lanes_budget > DEFAULT_MUTABLE_LANES
                or facts.review_lanes_budget > DEFAULT_REVIEW_LANES):
            return GuardResult(False, "RECONCILIATION_REQUIRED")
        verdict = classify_utilization(facts)
        metadata = {
            "a_faster_underutilized": verdict.a_faster_underutilized,
            "auto_refill_required": verdict.auto_refill_required,
            "fanout_target_mutable": verdict.fanout_target_mutable,
            "fanout_target_review": verdict.fanout_target_review,
            "blockers": verdict.blockers,
        }
        # A class comes from the bound scheduler, never from signal metadata.
        # When unspecified, do not borrow a free slot of the other class.
        if ((lane_class != "review" and facts.occupied_mutable_lanes >= facts.mutable_lanes_budget)
                or (lane_class != "mutable" and facts.occupied_review_lanes >= facts.review_lanes_budget)):
            return GuardResult(False, "CAPACITY_EXHAUSTED", metadata)
        selected_fanout = (verdict.fanout_target_mutable if lane_class == "mutable"
                           else verdict.fanout_target_review if lane_class == "review"
                           else verdict.fanout_target)
        if (facts.activation is not AFasterActivation.ACTIVE
                or facts.glm_quota_admission is not QuotaAdmission.QUOTA_AVAILABLE
                or not facts.glm_route_ready or selected_fanout == 0
                or (facts.sol_direct_long_labor_active and facts.sol_direct_labor_glm_eligible)):
            return GuardResult(False, "RECONCILIATION_REQUIRED", metadata)
        return GuardResult(True, "PASS", metadata)


class AuthorityGuard:
    """Application-bound current task/scope check, never read from payload."""

    def __init__(self, checker: Callable[[str, tuple[str, ...]], bool | None] | None = None):
        self._checker = checker

    def evaluate(self, signal: OrchestrationSignal, *, scope: tuple[str, ...] = (),
                 **_unused) -> GuardResult:
        invalid = _invalid_signal(signal)
        if invalid is not None:
            return invalid
        if signal.signal_type not in ("enqueue", "replay"):
            return GuardResult(False, "NOT_APPLICABLE")
        if (type(scope) is not tuple or not 1 <= len(scope) <= 64
                or any(type(item) is not str or not 1 <= len(item) <= 256
                       or item != item.strip() or any(ord(char) < 32 or ord(char) == 127 for char in item)
                       for item in scope)
                or len(set(scope)) != len(scope) or self._checker is None):
            return GuardResult(False, "AUTHORITY_DENIED")
        try:
            authorized = self._checker(signal.task_ref, scope)
        except Exception:
            return GuardResult(False, "AUTHORITY_DENIED")
        return GuardResult(authorized is True, "PASS" if authorized is True else "AUTHORITY_DENIED")


class GuardPipeline:
    """Fixed duplicate -> utilization -> authority with first-denial return.

    Guard implementations cannot be omitted/reordered by payload data. The
    checker is a trusted application port, NOT an external boolean receipt.
    Admission is local preflight only, not permission to bypass the existing
    dispatcher's final live authority/serialization checks.
    """

    def __init__(self, authority_checker: Callable[[str, tuple[str, ...]], bool | None] | None = None):
        self._authority = AuthorityGuard(authority_checker)

    def evaluate(self, signal: OrchestrationSignal, *, evidence: dict | None = None,
                 utilization_facts: UtilizationFacts | None = None,
                 scope: tuple[str, ...] = (), lane_class: str | None = None) -> GuardResult:
        invalid = _invalid_signal(signal)
        if invalid is not None:
            return invalid
        metadata = {}
        for name, guard in (("duplicate", DuplicateGuard()), ("utilization", UtilizationGuard()),
                            ("authority", self._authority)):
            try:
                result = guard.evaluate(signal, evidence=evidence,
                                        utilization_facts=utilization_facts, scope=scope,
                                        lane_class=lane_class)
            except Exception:
                return GuardResult(False, "RECONCILIATION_REQUIRED", {"stage": name})
            if (type(result) is not GuardResult or type(result.admitted) is not bool
                    or type(result.reason) is not str or type(result.metadata) is not dict):
                return GuardResult(False, "RECONCILIATION_REQUIRED", {"stage": name})
            metadata[name] = result.metadata
            if result.reason == "NOT_APPLICABLE":
                if name == "authority" and signal.signal_type in ("enqueue", "replay"):
                    return GuardResult(False, "AUTHORITY_DENIED", metadata)
                continue
            if not result.admitted:
                return GuardResult(False, result.reason, metadata)
        if signal.signal_type not in ("enqueue", "replay"):
            return GuardResult(False, "OBSERVED_ONLY", metadata)
        return GuardResult(True, "PASS", metadata)
