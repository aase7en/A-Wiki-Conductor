"""Deterministic run-history guard for bounded autonomous loops.

The guard is intentionally pure: it owns no scheduler, retry executor, store,
provider route, or side effect. Existing A-Conductor task/job authorities own
those concerns; this module only answers whether another iteration is allowed.

Concept adapted from cobusgreyling/loop-engineering's loop-context circuit
breaker (MIT), strengthened for A-Conductor's typed fail-closed contracts.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Sequence


class LoopOutcome(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    NOOP = "NOOP"


class LoopGuardReason(str, Enum):
    CONTINUE = "CONTINUE"
    MAX_ITERATIONS = "MAX_ITERATIONS"
    IDENTICAL_FAILURES = "IDENTICAL_FAILURES"
    NO_PROGRESS = "NO_PROGRESS"
    TOKEN_BUDGET = "TOKEN_BUDGET"
    ELAPSED_BUDGET = "ELAPSED_BUDGET"
    COST_BUDGET = "COST_BUDGET"


def _positive_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _nonnegative_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def _optional_nonnegative_int(value: object, field: str) -> int | None:
    if value is None:
        return None
    return _nonnegative_int(value, field)


def _nonnegative_number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a non-negative finite number")
    converted = float(value)
    if not math.isfinite(converted) or converted < 0:
        raise ValueError(f"{field} must be a non-negative finite number")
    return converted


def _optional_nonnegative_number(value: object, field: str) -> float | None:
    if value is None:
        return None
    return _nonnegative_number(value, field)


@dataclass(frozen=True)
class LoopAttempt:
    iteration: int
    outcome: LoopOutcome
    failure_key: str | None = None
    tokens_used: int = 0
    elapsed_seconds: float = 0.0
    estimated_cost_usd: float = 0.0

    def __post_init__(self) -> None:
        _positive_int(self.iteration, "iteration")
        if not isinstance(self.outcome, LoopOutcome):
            raise ValueError("outcome must be LoopOutcome")
        _nonnegative_int(self.tokens_used, "tokens_used")
        _nonnegative_number(self.elapsed_seconds, "elapsed_seconds")
        _nonnegative_number(self.estimated_cost_usd, "estimated_cost_usd")
        if self.outcome is LoopOutcome.FAILURE:
            if (
                not isinstance(self.failure_key, str)
                or not self.failure_key.strip()
                or len(self.failure_key) > 256
                or any(ch in self.failure_key for ch in "\r\n\x00")
            ):
                raise ValueError("failure_key is required for failure attempts")
        elif self.failure_key is not None:
            raise ValueError("failure_key is only valid for failure attempts")


@dataclass(frozen=True)
class LoopGuardPolicy:
    max_iterations: int = 10
    max_identical_failures: int = 3
    max_consecutive_failures: int = 5
    max_tokens: int | None = None
    max_elapsed_seconds: float | None = None
    max_estimated_cost_usd: float | None = None


    def __post_init__(self) -> None:
        _positive_int(self.max_iterations, "max_iterations")
        _positive_int(self.max_identical_failures, "max_identical_failures")
        _positive_int(self.max_consecutive_failures, "max_consecutive_failures")
        _optional_nonnegative_int(self.max_tokens, "max_tokens")
        _optional_nonnegative_number(self.max_elapsed_seconds, "max_elapsed_seconds")
        _optional_nonnegative_number(
            self.max_estimated_cost_usd, "max_estimated_cost_usd"
        )


@dataclass(frozen=True)
class LoopGuardMetrics:
    iterations: int
    attempt_records: int
    consecutive_failures: int
    identical_failure_streak: int
    tokens_used: int
    elapsed_seconds: float
    estimated_cost_usd: float


@dataclass(frozen=True)
class LoopGuardDecision:
    allowed: bool
    reason: LoopGuardReason
    metrics: LoopGuardMetrics


def _validate_history(attempts: Sequence[LoopAttempt]) -> None:
    previous = 0
    for item in attempts:
        if not isinstance(item, LoopAttempt):
            raise ValueError("attempt history must contain LoopAttempt values")
        if item.iteration <= previous:
            raise ValueError("attempt iterations must be strictly increasing")
        previous = item.iteration


def _trailing_failure_streaks(
    attempts: Sequence[LoopAttempt],
) -> tuple[int, int]:
    consecutive = 0
    for item in reversed(attempts):
        if item.outcome is not LoopOutcome.FAILURE:
            break
        consecutive += 1

    identical = 0
    last_key: str | None = None
    for item in reversed(attempts):
        if item.outcome is not LoopOutcome.FAILURE:
            break
        key = item.failure_key.strip() if item.failure_key is not None else None
        if last_key is None:
            last_key = key
        elif key != last_key:
            break
        identical += 1
    return consecutive, identical


def _metrics(attempts: Sequence[LoopAttempt]) -> LoopGuardMetrics:
    consecutive, identical = _trailing_failure_streaks(attempts)
    return LoopGuardMetrics(
        iterations=attempts[-1].iteration if attempts else 0,
        attempt_records=len(attempts),
        consecutive_failures=consecutive,
        identical_failure_streak=identical,
        tokens_used=sum(item.tokens_used for item in attempts),
        elapsed_seconds=sum(item.elapsed_seconds for item in attempts),
        estimated_cost_usd=sum(item.estimated_cost_usd for item in attempts),
    )


def evaluate_loop_guard(
    attempts: Sequence[LoopAttempt],
    policy: LoopGuardPolicy,
) -> LoopGuardDecision:
    """Return the deterministic decision before another iteration.

    Priority is stable and fail-closed: hard iteration cap, repeated identical
    failure, broader no-progress streak, then resource budgets.
    """
    if not isinstance(policy, LoopGuardPolicy):
        raise ValueError("policy must be LoopGuardPolicy")
    _validate_history(attempts)
    metrics = _metrics(attempts)

    reason = LoopGuardReason.CONTINUE

    if metrics.iterations >= policy.max_iterations:
        reason = LoopGuardReason.MAX_ITERATIONS
    elif metrics.identical_failure_streak >= policy.max_identical_failures:
        reason = LoopGuardReason.IDENTICAL_FAILURES
    elif metrics.consecutive_failures >= policy.max_consecutive_failures:
        reason = LoopGuardReason.NO_PROGRESS
    elif (
        attempts
        and policy.max_tokens is not None
        and metrics.tokens_used >= policy.max_tokens
    ):
        reason = LoopGuardReason.TOKEN_BUDGET
    elif (
        attempts
        and policy.max_elapsed_seconds is not None
        and metrics.elapsed_seconds >= policy.max_elapsed_seconds
    ):
        reason = LoopGuardReason.ELAPSED_BUDGET
    elif (
        attempts
        and policy.max_estimated_cost_usd is not None
        and metrics.estimated_cost_usd >= policy.max_estimated_cost_usd
    ):
        reason = LoopGuardReason.COST_BUDGET

    return LoopGuardDecision(
        allowed=reason is LoopGuardReason.CONTINUE,
        reason=reason,
        metrics=metrics,
    )


__all__ = [
    "LoopAttempt",
    "LoopGuardDecision",
    "LoopGuardMetrics",
    "LoopGuardPolicy",
    "LoopGuardReason",
    "LoopOutcome",
    "evaluate_loop_guard",
]
