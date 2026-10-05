from __future__ import annotations

import pytest

from a_conductor.loop_guard import (
    LoopAttempt,
    LoopGuardPolicy,
    LoopGuardReason,
    LoopOutcome,
    evaluate_loop_guard,
)


def attempt(
    iteration: int,
    outcome: LoopOutcome,
    *,
    failure_key: str | None = None,
    tokens: int = 0,
    elapsed: float = 0.0,
    cost: float = 0.0,
) -> LoopAttempt:
    return LoopAttempt(
        iteration=iteration,
        outcome=outcome,
        failure_key=failure_key,
        tokens_used=tokens,
        elapsed_seconds=elapsed,
        estimated_cost_usd=cost,
    )


def policy(**overrides: object) -> LoopGuardPolicy:
    values: dict[str, object] = {
        "max_iterations": 10,
        "max_identical_failures": 3,
        "max_consecutive_failures": 5,
    }
    values.update(overrides)
    return LoopGuardPolicy(**values)


def test_empty_and_healthy_history_continue() -> None:
    assert evaluate_loop_guard([], policy()).reason is LoopGuardReason.CONTINUE
    result = evaluate_loop_guard(
        [
            attempt(1, LoopOutcome.FAILURE, failure_key="BUILD_FAILED"),
            attempt(2, LoopOutcome.SUCCESS),
        ],
        policy(),
    )
    assert result.allowed is True
    assert result.reason is LoopGuardReason.CONTINUE


def test_iteration_cap_breaks_loop() -> None:
    history = [attempt(i, LoopOutcome.SUCCESS) for i in range(1, 4)]
    result = evaluate_loop_guard(history, policy(max_iterations=3))
    assert result.allowed is False
    assert result.reason is LoopGuardReason.MAX_ITERATIONS


def test_identical_failure_stagnation_breaks_loop() -> None:
    history = [
        attempt(1, LoopOutcome.FAILURE, failure_key="SAME"),
        attempt(2, LoopOutcome.FAILURE, failure_key="SAME"),
        attempt(3, LoopOutcome.FAILURE, failure_key="SAME"),
    ]
    result = evaluate_loop_guard(history, policy())
    assert result.reason is LoopGuardReason.IDENTICAL_FAILURES
    assert result.metrics.identical_failure_streak == 3


def test_distinct_consecutive_failures_hit_no_progress_cap() -> None:
    history = [
        attempt(i, LoopOutcome.FAILURE, failure_key=f"E{i}")
        for i in range(1, 6)
    ]
    result = evaluate_loop_guard(history, policy())
    assert result.reason is LoopGuardReason.NO_PROGRESS
    assert result.metrics.consecutive_failures == 5


@pytest.mark.parametrize(
    ("overrides", "history", "expected"),
    [
        ({"max_tokens": 100}, [attempt(1, LoopOutcome.SUCCESS, tokens=100)], LoopGuardReason.TOKEN_BUDGET),
        ({"max_elapsed_seconds": 5.0}, [attempt(1, LoopOutcome.SUCCESS, elapsed=5.0)], LoopGuardReason.ELAPSED_BUDGET),
        ({"max_estimated_cost_usd": 1.0}, [attempt(1, LoopOutcome.SUCCESS, cost=1.0)], LoopGuardReason.COST_BUDGET),
    ],
)
def test_resource_budgets_break_loop(
    overrides: dict[str, object],
    history: list[LoopAttempt],
    expected: LoopGuardReason,
) -> None:
    assert evaluate_loop_guard(history, policy(**overrides)).reason is expected


def test_success_resets_failure_streaks() -> None:
    history = [
        attempt(1, LoopOutcome.FAILURE, failure_key="E"),
        attempt(2, LoopOutcome.FAILURE, failure_key="E"),
        attempt(3, LoopOutcome.SUCCESS),
        attempt(4, LoopOutcome.FAILURE, failure_key="E"),
        attempt(5, LoopOutcome.FAILURE, failure_key="E"),
    ]
    result = evaluate_loop_guard(history, policy())
    assert result.allowed is True
    assert result.metrics.identical_failure_streak == 2
    assert result.metrics.consecutive_failures == 2


def test_hard_iteration_cap_has_deterministic_priority() -> None:
    history = [
        attempt(1, LoopOutcome.FAILURE, failure_key="E", tokens=100),
        attempt(2, LoopOutcome.FAILURE, failure_key="E", tokens=100),
    ]
    result = evaluate_loop_guard(
        history,
        policy(max_iterations=2, max_identical_failures=2, max_tokens=100),
    )
    assert result.reason is LoopGuardReason.MAX_ITERATIONS


def test_attempt_history_requires_strict_iteration_order() -> None:
    history = [
        attempt(2, LoopOutcome.SUCCESS),
        attempt(1, LoopOutcome.SUCCESS),
    ]
    with pytest.raises(ValueError, match="strictly increasing"):
        evaluate_loop_guard(history, policy())


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_iterations": 0},
        {"max_identical_failures": 0},
        {"max_consecutive_failures": 0},
        {"max_tokens": -1},
        {"max_elapsed_seconds": -1.0},
        {"max_estimated_cost_usd": -0.1},
    ],
)
def test_policy_rejects_invalid_limits(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        LoopGuardPolicy(**kwargs)


def test_failure_attempt_requires_stable_failure_key() -> None:
    with pytest.raises(ValueError, match="failure_key"):
        attempt(1, LoopOutcome.FAILURE)


def test_attempt_rejects_missing_token_accounting_value() -> None:
    with pytest.raises(ValueError, match="tokens_used"):
        LoopAttempt(
            iteration=1,
            outcome=LoopOutcome.SUCCESS,
            tokens_used=None,  # type: ignore[arg-type]
        )
