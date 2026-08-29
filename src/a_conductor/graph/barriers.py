"""GE-8 fan-out / fan-in completeness barriers.

Pure graph projection only. Dependency membership comes from ``TaskGraph``
edges and output expectations come from ``TaskNode.expected_outputs``. Durable
lifecycle truth is injected as explicit observations; this module owns no
scheduler, store, lifecycle, retry, execution, or UI behavior.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .domain import TaskGraph


def _text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must not be blank")
    return value.strip()


@dataclass(frozen=True, slots=True)
class FanInChildObservation:
    """Explicit lifecycle/output evidence for one graph child/predecessor."""

    node_id: str
    terminal: bool
    successful: bool = False
    skipped: bool = False
    observed_outputs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "node_id", _text(self.node_id, "node_id"))
        if not isinstance(self.terminal, bool):
            raise ValueError("terminal must be bool")
        if not isinstance(self.successful, bool):
            raise ValueError("successful must be bool")
        if not isinstance(self.skipped, bool):
            raise ValueError("skipped must be bool")
        if self.successful and self.skipped:
            raise ValueError("successful and skipped cannot both be true")
        if (self.successful or self.skipped) and not self.terminal:
            raise ValueError("successful or skipped observation must be terminal")
        outputs = tuple(
            _text(output_ref, f"observed_outputs[{index}]")
            for index, output_ref in enumerate(self.observed_outputs)
        )
        object.__setattr__(self, "observed_outputs", outputs)


@dataclass(frozen=True, slots=True)
class CompletenessBarrierResult:
    """Deterministic completeness state for one graph barrier anchor."""

    anchor_node_id: str
    expected_ids: tuple[str, ...]
    missing_ids: tuple[str, ...]
    pending_ids: tuple[str, ...]
    successful_ids: tuple[str, ...]
    failed_ids: tuple[str, ...]
    skipped_ids: tuple[str, ...]
    silent_ids: tuple[str, ...]
    output_gaps: tuple[tuple[str, tuple[str, ...]], ...]

    @property
    def is_complete(self) -> bool:
        return not (self.missing_ids or self.pending_ids or self.silent_ids)

    @property
    def is_satisfied(self) -> bool:
        return self.is_complete and not self.failed_ids


def _normalize_observations(
    observations: Mapping[str, FanInChildObservation],
) -> dict[str, FanInChildObservation]:
    if not isinstance(observations, Mapping):
        raise ValueError("observations must be a mapping")
    normalized: dict[str, FanInChildObservation] = {}
    for key, observation in observations.items():
        key = _text(key, "observation key")
        if not isinstance(observation, FanInChildObservation):
            raise ValueError("observation values must be FanInChildObservation")
        if key != observation.node_id:
            raise ValueError("observation identity must match mapping key")
        normalized[key] = observation
    return normalized


def _expected_outputs(graph: TaskGraph, node_id: str) -> set[str]:
    outputs: set[str] = set()
    for index, output_ref in enumerate(graph.node(node_id).expected_outputs):
        outputs.add(_text(output_ref, f"{node_id}.expected_outputs[{index}]"))
    return outputs


def _evaluate_expected_children(
    graph: TaskGraph,
    target_node_id: str,
    expected_ids: tuple[str, ...],
    observations: Mapping[str, FanInChildObservation],
) -> CompletenessBarrierResult:
    normalized = _normalize_observations(observations)
    missing: list[str] = []
    pending: list[str] = []
    successful: list[str] = []
    failed: list[str] = []
    skipped: list[str] = []
    silent: list[str] = []
    output_gaps: list[tuple[str, tuple[str, ...]]] = []

    for child_id in expected_ids:
        observation = normalized.get(child_id)
        if observation is None:
            missing.append(child_id)
            continue
        if not observation.terminal:
            pending.append(child_id)
            continue
        if observation.successful:
            successful.append(child_id)
        elif observation.skipped:
            skipped.append(child_id)
        else:
            failed.append(child_id)
            continue

        expected_outputs = _expected_outputs(graph, child_id)
        observed_outputs = set(observation.observed_outputs)
        missing_outputs = tuple(sorted(expected_outputs - observed_outputs))
        if missing_outputs:
            silent.append(child_id)
            output_gaps.append((child_id, missing_outputs))

    return CompletenessBarrierResult(
        anchor_node_id=target_node_id,
        expected_ids=expected_ids,
        missing_ids=tuple(missing),
        pending_ids=tuple(pending),
        successful_ids=tuple(successful),
        failed_ids=tuple(failed),
        skipped_ids=tuple(skipped),
        silent_ids=tuple(silent),
        output_gaps=tuple(output_gaps),
    )


def _require_graph_node(graph: TaskGraph, node_id: str, field: str) -> str:
    if not isinstance(graph, TaskGraph):
        raise ValueError("graph must be TaskGraph")
    node_id = _text(node_id, field)
    if node_id not in set(graph.node_ids()):
        raise ValueError(f"unknown {field.replace('_', ' ')}: {node_id}")
    return node_id


def evaluate_fan_in_barrier(
    graph: TaskGraph,
    target_node_id: str,
    observations: Mapping[str, FanInChildObservation],
) -> CompletenessBarrierResult:
    """Evaluate completeness of all predecessors feeding a join node."""

    target_node_id = _require_graph_node(graph, target_node_id, "target_node_id")
    expected_ids = tuple(
        sorted({edge.from_id for edge in graph.edges_to(target_node_id)})
    )
    return _evaluate_expected_children(
        graph, target_node_id, expected_ids, observations
    )


def evaluate_fan_out_barrier(
    graph: TaskGraph,
    parent_node_id: str,
    observations: Mapping[str, FanInChildObservation],
) -> CompletenessBarrierResult:
    """Evaluate completeness of all children fanned out from a parent node."""

    parent_node_id = _require_graph_node(graph, parent_node_id, "parent_node_id")
    expected_ids = tuple(
        sorted({edge.to_id for edge in graph.edges_from(parent_node_id)})
    )
    return _evaluate_expected_children(
        graph, parent_node_id, expected_ids, observations
    )
