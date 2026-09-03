"""ODP-1 — pure Orchestration Packet v1 projection.

This module is a data-minimization boundary between durable A-Conductor runtime
state and a future non-mutating planner/adjudicator.  It does not invoke a
model, probe a provider, select/admit a route, mutate a TaskGraph, read a
repository, resolve credentials, or dispatch work.

The packet deliberately projects an allowlisted subset of ``task-contract/v1``
and current graph/runtime facts.  Arbitrary task metadata, requester/approver
identity, command strings, endpoint/network targets, legacy model requirements,
credentials, transcripts, and environment data are not copied across this
boundary.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import re
from typing import Mapping, Sequence

from .graph.domain import TaskGraph, TaskNodeStatus
from .graph.ready import compute_ready_set


ORCHESTRATION_PACKET_SCHEMA_VERSION = "orchestration-packet/v1"
_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,64}$")
_TASK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
_TASK_ROOT_ALLOWED = frozenset({"schema_version", "task_id", "work_order_ref", "goal", "task_type", "risk_class", "authority", "target", "scope", "acceptance", "security", "routing", "budget", "retry_policy", "escalation", "required_evidence", "metadata"})
_RISK_CLASSES = frozenset({"LOW", "NORMAL", "HIGH", "HUMAN_REQUIRED"})
_IDENTITY_POLICIES = frozenset({"EXACT", "AUTHORIZED_SUCCESSOR", "NO_GIT", "READ_ONLY_DISCOVERY"})
_SCOPE_GROWTH = frozenset({"FORBIDDEN", "AMENDMENT_REQUIRED"})
_PRIVACY_CLASSES = frozenset({"PUBLIC", "INTERNAL", "SENSITIVE", "SECRET"})
_NETWORK_POLICIES = frozenset({"DENIED", "ALLOWLISTED", "INHERIT"})
_ESCALATION_CONDITIONS = frozenset({"ARCHITECTURE_DECISION", "SECURITY_BOUNDARY_CHANGE", "DESTRUCTIVE_OPERATION", "CREDENTIALS_REQUIRED", "MERGE_CONFLICT", "BASELINE_INVALID", "REPEATED_FAILURE", "SCOPE_EXPANSION", "PROVIDER_BEHAVIOR_DRIFT", "PRIVACY_RISK", "IDENTITY_MISMATCH", "UNKNOWN_RECOVERY_STATE"})
_EVIDENCE_CLASSES = frozenset({"REPOSITORY_IDENTITY", "CHANGED_FILES", "DIFF_SUMMARY", "COMMAND_RESULT", "TEST_RESULT", "LINT_RESULT", "TYPECHECK_RESULT", "CHECKSUM", "HEALTH_CHECK", "REVIEW_RESULT", "SCOPE_DEVIATION_REPORT"})


def _text(value: object, field: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-blank string")
    return value.strip()


def _bool(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be bool")
    return value


def _positive_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _nonblank_tuple(values: Sequence[str], field: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ValueError(f"{field} must be a sequence of non-blank strings")
    normalized: list[str] = []
    for value in values:
        text = _text(value, field)
        assert text is not None
        normalized.append(text)
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{field} must not contain duplicates")
    return tuple(normalized)


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    return value


def _keys(value: Mapping[str, object], field: str, *, required: set[str], allowed: set[str]) -> None:
    keys = set(value)
    missing = required - keys
    if missing:
        raise ValueError(f"{field}.{sorted(missing)[0]} is required")
    extra = keys - allowed
    if extra:
        raise ValueError(f"{field}.{sorted(extra)[0]} is not valid for task-contract/v1")


def _enum(value: object, field: str, allowed: frozenset[str]) -> str:
    text = _text(value, field)
    assert text is not None
    if text not in allowed:
        raise ValueError(f"{field} is invalid")
    return text


def _nonnegative_int_or_none(value: object, field: str) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer or None")


def _nonnegative_number_or_none(value: object, field: str) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ValueError(f"{field} must be a non-negative number or None")


def _validate_task_contract_v1(task: Mapping[str, object]) -> None:
    required_root = {"schema_version", "task_id", "goal", "risk_class", "authority", "target", "scope", "acceptance", "security", "budget", "retry_policy", "escalation", "required_evidence"}
    _keys(task, "task_contract", required=required_root, allowed=set(_TASK_ROOT_ALLOWED))
    if task.get("schema_version") != "1.0.0":
        raise ValueError("task_contract.schema_version must be 1.0.0")
    task_id = _text(task.get("task_id"), "task_contract.task_id")
    assert task_id is not None
    if _TASK_ID_RE.fullmatch(task_id) is None:
        raise ValueError("task_contract.task_id is invalid")
    goal = _text(task.get("goal"), "task_contract.goal")
    assert goal is not None
    if len(goal) > 10000:
        raise ValueError("task_contract.goal is too long")
    _enum(task.get("risk_class"), "task_contract.risk_class", _RISK_CLASSES)

    authority = _mapping(task.get("authority"), "task_contract.authority")
    _keys(authority, "task_contract.authority", required={"requested_by", "mutation_allowed", "human_approval_required"}, allowed={"requested_by", "approved_by", "approval_ref", "mutation_allowed", "human_approval_required"})
    _text(authority.get("requested_by"), "task_contract.authority.requested_by")
    _bool(authority.get("mutation_allowed"), "task_contract.authority.mutation_allowed")
    _bool(authority.get("human_approval_required"), "task_contract.authority.human_approval_required")

    target = _mapping(task.get("target"), "task_contract.target")
    _keys(target, "task_contract.target", required={"project_id", "identity_policy"}, allowed={"project_id", "repository_identity_ref", "expected_worktree_path", "expected_branch", "expected_head", "identity_policy"})
    _text(target.get("project_id"), "task_contract.target.project_id")
    _enum(target.get("identity_policy"), "task_contract.target.identity_policy", _IDENTITY_POLICIES)
    head = target.get("expected_head")
    if head is not None and (not isinstance(head, str) or _SHA_RE.fullmatch(head) is None):
        raise ValueError("task_contract.target.expected_head is invalid")

    scope = _mapping(task.get("scope"), "task_contract.scope")
    _keys(scope, "task_contract.scope", required={"allowed_files", "forbidden_files", "allowed_commands", "forbidden_commands"}, allowed={"allowed_files", "forbidden_files", "allowed_commands", "forbidden_commands", "max_changed_files", "max_diff_bytes", "scope_growth"})
    for name in ("allowed_files", "forbidden_files", "allowed_commands", "forbidden_commands"):
        _nonblank_tuple(scope.get(name), f"task_contract.scope.{name}")  # type: ignore[arg-type]
    _nonnegative_int_or_none(scope.get("max_changed_files"), "task_contract.scope.max_changed_files")
    _nonnegative_int_or_none(scope.get("max_diff_bytes"), "task_contract.scope.max_diff_bytes")
    if "scope_growth" in scope:
        _enum(scope.get("scope_growth"), "task_contract.scope.scope_growth", _SCOPE_GROWTH)

    acceptance = _mapping(task.get("acceptance"), "task_contract.acceptance")
    _keys(acceptance, "task_contract.acceptance", required={"criteria", "verify_commands", "review_required"}, allowed={"criteria", "verify_commands", "review_required", "required_review_class"})
    criteria = _nonblank_tuple(acceptance.get("criteria"), "task_contract.acceptance.criteria")  # type: ignore[arg-type]
    if not criteria:
        raise ValueError("task_contract.acceptance.criteria must not be empty")
    _nonblank_tuple(acceptance.get("verify_commands"), "task_contract.acceptance.verify_commands")  # type: ignore[arg-type]
    _bool(acceptance.get("review_required"), "task_contract.acceptance.review_required")

    security = _mapping(task.get("security"), "task_contract.security")
    _keys(security, "task_contract.security", required={"privacy_class", "network_policy", "secret_access"}, allowed={"privacy_class", "network_policy", "network_allowlist", "secret_access"})
    _enum(security.get("privacy_class"), "task_contract.security.privacy_class", _PRIVACY_CLASSES)
    _enum(security.get("network_policy"), "task_contract.security.network_policy", _NETWORK_POLICIES)
    _bool(security.get("secret_access"), "task_contract.security.secret_access")

    budget = _mapping(task.get("budget"), "task_contract.budget")
    _keys(budget, "task_contract.budget", required={"max_elapsed_seconds"}, allowed={"max_elapsed_seconds", "max_input_tokens", "max_output_tokens", "max_estimated_cost_usd"})
    _positive_int(budget.get("max_elapsed_seconds"), "task_contract.budget.max_elapsed_seconds")
    _nonnegative_int_or_none(budget.get("max_input_tokens"), "task_contract.budget.max_input_tokens")
    _nonnegative_int_or_none(budget.get("max_output_tokens"), "task_contract.budget.max_output_tokens")
    _nonnegative_number_or_none(budget.get("max_estimated_cost_usd"), "task_contract.budget.max_estimated_cost_usd")

    retry = _mapping(task.get("retry_policy"), "task_contract.retry_policy")
    _keys(retry, "task_contract.retry_policy", required={"max_attempts", "max_identical_failures", "on_lease_expiry"}, allowed={"max_attempts", "max_identical_failures", "on_lease_expiry"})
    _positive_int(retry.get("max_attempts"), "task_contract.retry_policy.max_attempts")
    _positive_int(retry.get("max_identical_failures"), "task_contract.retry_policy.max_identical_failures")
    if retry.get("on_lease_expiry") != "RECOVERY_REQUIRED":
        raise ValueError("task_contract.retry_policy.on_lease_expiry is invalid")

    escalation = _mapping(task.get("escalation"), "task_contract.escalation")
    _keys(escalation, "task_contract.escalation", required={"conditions"}, allowed={"conditions"})
    conditions = _nonblank_tuple(escalation.get("conditions"), "task_contract.escalation.conditions")  # type: ignore[arg-type]
    if any(item not in _ESCALATION_CONDITIONS for item in conditions):
        raise ValueError("task_contract.escalation.conditions is invalid")
    evidence = _nonblank_tuple(task.get("required_evidence"), "task_contract.required_evidence")  # type: ignore[arg-type]
    if not evidence or any(item not in _EVIDENCE_CLASSES for item in evidence):
        raise ValueError("task_contract.required_evidence is invalid")

def _selected(source: Mapping[str, object], keys: Sequence[str]) -> dict[str, object]:
    return {key: deepcopy(source[key]) for key in keys if key in source}


def _json_safe(value: object, field: str) -> None:
    try:
        json.dumps(value, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be JSON-safe") from exc


@dataclass(frozen=True, slots=True)
class RepositoryFacts:
    """Already-observed repository/authority facts; this class performs no I/O."""

    project_id: str
    repository_ref: str | None
    worktree_ref: str | None
    branch: str | None
    head_sha: str | None
    dirty: bool
    identity_verified: bool
    mutation_authorized: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _text(self.project_id, "project_id"))
        for field in ("repository_ref", "worktree_ref", "branch"):
            object.__setattr__(self, field, _text(getattr(self, field), field, optional=True))
        head = _text(self.head_sha, "head_sha", optional=True)
        if head is not None and _SHA_RE.fullmatch(head) is None:
            raise ValueError("head_sha must be 7-64 hexadecimal characters when set")
        object.__setattr__(self, "head_sha", head)
        _bool(self.dirty, "dirty")
        _bool(self.identity_verified, "identity_verified")
        _bool(self.mutation_authorized, "mutation_authorized")
        if self.mutation_authorized and not self.identity_verified:
            raise ValueError("mutation_authorized requires identity_verified")

    def to_dict(self) -> dict[str, object]:
        return {
            "project_id": self.project_id,
            "repository_ref": self.repository_ref,
            "worktree_ref": self.worktree_ref,
            "branch": self.branch,
            "head_sha": self.head_sha,
            "dirty": self.dirty,
            "identity_verified": self.identity_verified,
            "mutation_authorized": self.mutation_authorized,
        }


@dataclass(frozen=True, slots=True)
class EligibleRouteCandidate:
    """A candidate that upstream authority has already deemed eligible.

    This type intentionally has no READY/AUTHORIZED/ADMITTED booleans.  ODP-1
    does not recreate provider admission policy; callers may construct this
    object only after those existing authorities have accepted the route.
    """

    candidate_id: str
    actor_role: str
    provider_id: str | None = None
    model_id: str | None = None
    capabilities: tuple[str, ...] = ()
    supports_long_running: bool = False
    supports_resume: bool = False
    supports_background_execution: bool = False
    supports_repo_tools: bool = False
    requires_human_presence: bool = False
    max_concurrency: int = 1
    cost_class: str | None = None
    quota_state: str | None = None
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidate_id", _text(self.candidate_id, "candidate_id"))
        object.__setattr__(self, "actor_role", _text(self.actor_role, "actor_role"))
        for field in ("provider_id", "model_id", "cost_class", "quota_state"):
            object.__setattr__(self, field, _text(getattr(self, field), field, optional=True))
        object.__setattr__(self, "capabilities", _nonblank_tuple(self.capabilities, "capabilities"))
        object.__setattr__(self, "evidence_refs", _nonblank_tuple(self.evidence_refs, "evidence_refs"))
        for field in (
            "supports_long_running",
            "supports_resume",
            "supports_background_execution",
            "supports_repo_tools",
            "requires_human_presence",
        ):
            _bool(getattr(self, field), field)
        object.__setattr__(self, "max_concurrency", _positive_int(self.max_concurrency, "max_concurrency"))

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "actor_role": self.actor_role,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "capabilities": list(self.capabilities),
            "surface_traits": {
                "supports_long_running": self.supports_long_running,
                "supports_resume": self.supports_resume,
                "supports_background_execution": self.supports_background_execution,
                "supports_repo_tools": self.supports_repo_tools,
                "requires_human_presence": self.requires_human_presence,
            },
            "max_concurrency": self.max_concurrency,
            "cost_class": self.cost_class,
            "quota_state": self.quota_state,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class OrchestrationPacket:
    task: dict[str, object]
    graph_id: str
    graph_nodes: tuple[dict[str, object], ...]
    graph_edges: tuple[dict[str, object], ...]
    ready_frontier: tuple[str, ...]
    repository: RepositoryFacts
    eligible_candidates: tuple[EligibleRouteCandidate, ...]
    policy_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    blockers: tuple[str, ...]
    max_parallelism: int
    max_adjudication_rounds: int
    schema_version: str = ORCHESTRATION_PACKET_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        payload = {
            "schema_version": self.schema_version,
            "task": deepcopy(self.task),
            "graph": {
                "graph_id": self.graph_id,
                "nodes": [deepcopy(node) for node in self.graph_nodes],
                "edges": [deepcopy(edge) for edge in self.graph_edges],
                "ready_frontier": list(self.ready_frontier),
            },
            "repository": self.repository.to_dict(),
            "eligible_candidates": [candidate.to_dict() for candidate in self.eligible_candidates],
            "policy_refs": list(self.policy_refs),
            "evidence_refs": list(self.evidence_refs),
            "blockers": list(self.blockers),
            "limits": {
                "max_parallelism": self.max_parallelism,
                "max_adjudication_rounds": self.max_adjudication_rounds,
            },
        }
        _json_safe(payload, "orchestration packet")
        return payload


def _project_task_contract(task_contract: Mapping[str, object]) -> dict[str, object]:
    _validate_task_contract_v1(task_contract)
    required_objects = (
        "authority",
        "target",
        "scope",
        "acceptance",
        "security",
        "budget",
        "retry_policy",
        "escalation",
    )
    for field in ("task_id", "goal", "risk_class", "required_evidence"):
        if field not in task_contract:
            raise ValueError(f"task_contract.{field} is required")
    objects = {field: _mapping(task_contract.get(field), f"task_contract.{field}") for field in required_objects}
    routing = _mapping(task_contract.get("routing", {}), "task_contract.routing")
    routing_traits = _mapping(
        routing.get("preferred_surface_traits", {}),
        "task_contract.routing.preferred_surface_traits",
    )

    task_id = _text(task_contract["task_id"], "task_contract.task_id")
    goal = _text(task_contract["goal"], "task_contract.goal")
    risk_class = _text(task_contract["risk_class"], "task_contract.risk_class")
    required_evidence = _nonblank_tuple(task_contract["required_evidence"], "task_contract.required_evidence")  # type: ignore[arg-type]

    projection: dict[str, object] = {
        "task_contract_schema_version": deepcopy(task_contract.get("schema_version")),
        "task_id": task_id,
        "goal": goal,
        "risk_class": risk_class,
        "authority": _selected(objects["authority"], ("mutation_allowed", "human_approval_required")),
        "target": _selected(
            objects["target"],
            ("project_id", "repository_identity_ref", "expected_branch", "expected_head", "identity_policy"),
        ),
        "scope": _selected(
            objects["scope"],
            ("allowed_files", "forbidden_files", "max_changed_files", "max_diff_bytes", "scope_growth"),
        ),
        "acceptance": _selected(objects["acceptance"], ("criteria", "review_required", "required_review_class")),
        "security": _selected(objects["security"], ("privacy_class", "network_policy", "secret_access")),
        "routing": {
            **_selected(routing, ("required_capabilities",)),
            "preferred_surface_traits": _selected(
                routing_traits,
                (
                    "supports_long_running",
                    "supports_resume",
                    "supports_background_execution",
                    "supports_repo_tools",
                    "requires_human_presence",
                    "max_safe_transaction_scope",
                ),
            ),
        },
        "budget": _selected(
            objects["budget"],
            ("max_elapsed_seconds", "max_input_tokens", "max_output_tokens", "max_estimated_cost_usd"),
        ),
        "retry_policy": _selected(
            objects["retry_policy"], ("max_attempts", "max_identical_failures", "on_lease_expiry")
        ),
        "escalation": _selected(objects["escalation"], ("conditions",)),
        "required_evidence": list(required_evidence),
    }
    if "work_order_ref" in task_contract and task_contract["work_order_ref"] is not None:
        projection["work_order_ref"] = _text(task_contract["work_order_ref"], "task_contract.work_order_ref")
    if "task_type" in task_contract and task_contract["task_type"] is not None:
        projection["task_type"] = _text(task_contract["task_type"], "task_contract.task_type")

    _json_safe(projection, "task_contract projection")
    return projection


def _project_graph(
    graph: TaskGraph,
    node_states: Mapping[str, TaskNodeStatus],
) -> tuple[tuple[dict[str, object], ...], tuple[dict[str, object], ...], tuple[str, ...]]:
    if not isinstance(graph, TaskGraph):
        raise ValueError("graph must be TaskGraph")
    node_ids = set(graph.node_ids())
    unknown = set(node_states) - node_ids
    if unknown:
        raise ValueError(f"node_states contains unknown node ids: {', '.join(sorted(unknown))}")
    for node_id, state in node_states.items():
        if not isinstance(state, TaskNodeStatus):
            raise ValueError(f"node_states[{node_id!r}] must be TaskNodeStatus")

    ready = compute_ready_set(graph, dict(node_states))
    nodes: list[dict[str, object]] = []
    for node in sorted(graph.nodes(), key=lambda item: item.id):
        effective_status = node_states.get(node.id, TaskNodeStatus.TODO)
        nodes.append(
            {
                "id": node.id,
                "objective": node.objective,
                "expected_outputs": list(node.expected_outputs),
                "read_set": list(node.read_set),
                "write_set": list(node.write_set),
                "worker_requirement": list(node.worker_requirement),
                "priority": node.priority,
                "timeout_seconds": node.timeout_seconds,
                "retry_policy_ref": node.retry_policy_ref,
                "status": effective_status.value,
                "artifacts": list(node.artifacts),
            }
        )
    edges = tuple(
        {
            "from_id": edge.from_id,
            "to_id": edge.to_id,
            "dependency_type": edge.dep_type.value,
        }
        for edge in sorted(graph.edges(), key=lambda item: (item.from_id, item.to_id, item.dep_type.value))
    )
    _json_safe(nodes, "graph node projection")
    _json_safe(edges, "graph edge projection")
    return tuple(nodes), edges, tuple(sorted(ready.ready_ids))


def build_orchestration_packet(
    *,
    task_contract: Mapping[str, object],
    graph: TaskGraph,
    node_states: Mapping[str, TaskNodeStatus],
    graph_id: str,
    repository: RepositoryFacts,
    eligible_candidates: Sequence[EligibleRouteCandidate],
    policy_refs: Sequence[str] = (),
    evidence_refs: Sequence[str] = (),
    blockers: Sequence[str] = (),
    max_parallelism: int = 1,
    max_adjudication_rounds: int = 3,
) -> OrchestrationPacket:
    """Build one deterministic, minimized packet from already-observed state.

    Candidate eligibility is intentionally an input precondition.  This function
    does not decide whether a provider is READY/AUTHORIZED/ADMITTED and therefore
    cannot weaken the existing provider execution-authority boundary.
    """

    if not isinstance(task_contract, Mapping):
        raise ValueError("task_contract must be an object")
    if not isinstance(repository, RepositoryFacts):
        raise ValueError("repository must be RepositoryFacts")
    graph_id_value = _text(graph_id, "graph_id")
    assert graph_id_value is not None
    parallelism = _positive_int(max_parallelism, "max_parallelism")
    rounds = _positive_int(max_adjudication_rounds, "max_adjudication_rounds")

    candidates = tuple(eligible_candidates)
    if any(not isinstance(candidate, EligibleRouteCandidate) for candidate in candidates):
        raise ValueError("eligible_candidates must contain EligibleRouteCandidate values")
    candidate_ids = [candidate.candidate_id for candidate in candidates]
    if len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("duplicate eligible candidate_id")
    candidates = tuple(sorted(candidates, key=lambda item: item.candidate_id))

    task = _project_task_contract(task_contract)
    graph_nodes, graph_edges, ready_frontier = _project_graph(graph, node_states)

    packet = OrchestrationPacket(
        task=task,
        graph_id=graph_id_value,
        graph_nodes=graph_nodes,
        graph_edges=graph_edges,
        ready_frontier=ready_frontier,
        repository=repository,
        eligible_candidates=candidates,
        policy_refs=_nonblank_tuple(policy_refs, "policy_refs"),
        evidence_refs=_nonblank_tuple(evidence_refs, "evidence_refs"),
        blockers=_nonblank_tuple(blockers, "blockers"),
        max_parallelism=parallelism,
        max_adjudication_rounds=rounds,
    )
    packet.to_dict()  # prove the complete boundary is JSON-safe before returning it
    return packet
